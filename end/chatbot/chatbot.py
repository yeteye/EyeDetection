import re
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from typing import List
import faiss
import numpy as np
import pickle
import os

def split_text_by_empty_lines_robust(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            content = content.replace('\r\n', '\n')
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
            return paragraphs
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='gbk') as file:
            content = file.read()
            content = content.replace('\r\n', '\n')
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
            return paragraphs

def get_embeddings(texts: List[str], client, batch_size: int = 8) -> List[List[float]]:
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model="text-embedding-3-large",
            encoding_format="float"
        )
        embeddings.extend([data.embedding for data in response.data])
    return embeddings

class VectorStore:
    def __init__(self):
        self.dimension = 3072  # text-embedding-3-large的维度
        self.index = faiss.IndexFlatL2(self.dimension)
        self.texts = []

    def add_texts(self, texts: List[str], embeddings: List[List[float]]):
        vectors = np.array(embeddings).astype('float32')
        self.index.add(vectors)
        self.texts.extend(texts)

    def save(self, index_path: str, texts_path: str):
        faiss.write_index(self.index, index_path)
        with open(texts_path, 'wb') as f:
            pickle.dump(self.texts, f)

    @classmethod
    def load(cls, index_path: str, texts_path: str):
        store = cls()
        store.index = faiss.read_index(index_path)
        with open(texts_path, 'rb') as f:
            store.texts = pickle.load(f)
        return store

    def search(self, query_embedding: List[float], k: int = 5) -> List[str]:
        query_vector = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(query_vector, k)

        results = []
        for idx in indices[0]:
            if idx >= 0 and idx < len(self.texts):
                results.append(self.texts[idx])
        return results

def setup_vector_store(file_path: str, client,save_dir: str = "vector_store"):
    os.makedirs(save_dir, exist_ok=True)
    chunks = split_text_by_empty_lines_robust(file_path)
    embeddings = get_embeddings(chunks, client)

    store = VectorStore()
    store.add_texts(chunks, embeddings)
    store.save(
        os.path.join(save_dir, "eye_disease.index"),
        os.path.join(save_dir, "eye_disease_texts.pkl")
    )
    print("向量存储已保存到本地")
    return store

def search_similar_texts(query: str, store: VectorStore, client: OpenAI) -> List[str]:
    query_embedding = get_embeddings([query], client)[0]
    similar_texts = store.search(query_embedding, k=5)
    return similar_texts

class DialogueManager:
    def __init__(self, client, store):
        self.client = client
        self.store = store
        self.history = []

    def _format_history(self):
        return [{"role": "user" if i % 2 == 0 else "assistant",
                 "content": msg} for i, msg in enumerate(self.history)]

    def process_query(self, query: str) -> str:
        SYSTEM_PROMPT = """
            # 角色设定
            你是一名严谨的眼科医学知识助手，专门根据提供的医学文献片段回答用户关于眼部疾病的查询。你的回答必须基于提供的资料，不得掺杂外部知识或主观推测。

            # 输入数据格式
            用户将按以下结构提供信息：
            [查询主题]: 用户提出的具体问题
            [相关片段]: 由系统检索出的5个最相似文本段落

            # 处理流程
            1. 相关性判断阶段：
            - 若查询涉及非眼科疾病（如牙科/皮肤科疾病）或与医疗无关（如烹饪/编程），立即回应："抱歉，我专注于眼科疾病领域的问题，暂时无法回答其他类型的咨询。"
            - 若属于眼科范畴则进入下一阶段

            2. 内容验证阶段：
            a) 交叉核对所有片段与查询的医学相关性
            b) 发现片段间矛盾时补充说明："需要提醒，不同文献中存在表述差异..."

            3. 回答生成要求：
            ■ 严格遵循片段证据链，禁止任何形式的知识延伸
            ■ 专业表述需转换为患者易懂的科普语言
            ■ 出现以下情况时委婉拒绝：
               - 片段未覆盖关键病理机制（如询问发病机制但片段无记载）
               - 涉及治疗方案但无具体药物/手术描述
               - 存在诊断标准但缺少分期分型说明
            ■ 拒绝话术示例："根据现有资料，我们暂时无法给出确切结论，建议咨询专业眼科医师进行详细检查"

            # 输出规范
            ✓ 采用分点式临床建议框架（病因分析→诊断要点→治疗原则）
            ✓ 必须中文口语化表达
            ✓ 响应长度控制在300字内
            """
        similar_texts = search_similar_texts(query, self.store, self.client)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self._format_history(),
            {"role": "user", "content": f"[当前查询]: {query}\n[相关片段]:\n" + "\n".join(similar_texts)}
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=400
        ).choices[0].message.content

        self.history.extend([query, response])
        return response

if __name__ == "__main__":
    client = OpenAI(
        base_url="https://api.gptsapi.net/v1",
        api_key="sk-peade5e1f9308077da23d30f3d98315b9d6e6258b34uHZuT"
    )
    store = VectorStore.load("vector_store/eye_disease.index",
                             "vector_store/eye_disease_texts.pkl")
    dialog = DialogueManager(client, store)

    print("眼科医学知识小助手: 你好，我是眼科医学知识助手。你可以问我关于眼部疾病的问题，输入'退出'退出对话。")
    while True:
        try:
            user_input = input("\n你：")
            if user_input.lower() in ['退出', 'exit']:
                break

            response = dialog.process_query(user_input)
            print(f"\n眼科医学知识小助手：{response}")

        except KeyboardInterrupt:
            print("\n对话已终止")
            break
        except Exception as e:
            print(e)
            print(f"\n系统错误：{str(e)}")

'''
青光眼病因是什么？
我要做哪些检查呢？
青光眼怎么治疗呢？
退出
'''