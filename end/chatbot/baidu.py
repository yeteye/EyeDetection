import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from difflib import SequenceMatcher
from collections import OrderedDict


def calculate_similarity(str1, str2):
    """
    计算两个字符串的相似度
    """
    return SequenceMatcher(None, str1, str2).ratio()


def remove_similar_paragraphs(paragraphs, similarity_threshold=0.85):
    """
    去除相似度高于阈值的段落
    """
    unique_paragraphs = []

    for current_para in paragraphs:
        # 跳过空段落
        if not current_para.strip():
            continue

        # 检查是否与已保存的段落相似
        is_similar = False
        for existing_para in unique_paragraphs:
            if calculate_similarity(current_para, existing_para) > similarity_threshold:
                is_similar = True
                break

        if not is_similar:
            unique_paragraphs.append(current_para)

    return unique_paragraphs


def web_content_extractor(url):
    """
    网页正文内容提取函数
    参数：url - 需要抓取的完整网页地址
    返回：清理后的文本内容或错误信息
    """
    # 验证URL有效性
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return "无效的URL格式，请输入完整的网址（包含http/https协议头）"
    except:
        return "URL解析异常，请检查输入格式"

    # 配置请求参数
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    }

    try:
        # 发送带超时设置的请求
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # 自动检测编码
        if response.encoding:
            response.encoding = response.apparent_encoding if 'charset' not in response.headers.get('content-type',
                                                                                                    '') else response.encoding

        soup = BeautifulSoup(response.text, 'lxml')

        # 智能定位正文区域
        content_containers = [
            soup.find('article'),
            soup.find('div', class_='content'),
            soup.find('div', class_='article-content'),
            soup.find('div', class_='main-content'),
            soup.find('div', id='content')
        ]

        content_div = next((item for item in content_containers if item is not None), None)

        if not content_div:
            content_div = soup.body or soup

        # 清理干扰元素
        for element in content_div(['script', 'style', 'nav', 'footer', 'aside', 'form', 'button', 'iframe']):
            element.decompose()

        # 提取段落
        paragraphs = [
            p.get_text(strip=True)
            for p in content_div.find_all(['p', 'div'], recursive=True)
            if len(p.get_text(strip=True)) > 20  # 过滤短文本段落
        ]

        # 去除重复段落
        unique_paragraphs = remove_similar_paragraphs(paragraphs)

        # 组合成最终文本
        text_content = '\n\n'.join(unique_paragraphs)

        return text_content if text_content.strip() else "未检测到有效正文内容"

    except requests.exceptions.RequestException as e:
        return f"网络请求失败：{str(e)}"
    except Exception as e:
        return f"解析异常：{str(e)}"


def main():
    """
    主函数，包含输入输出和结果统计
    """
    input_url = input("请输入要抓取的网页URL：")
    print("\n正在处理...")

    result = web_content_extractor(input_url)

    if isinstance(result, str) and not result.startswith(("网络请求失败", "解析异常", "无效的URL", "未检测到")):
        paragraphs = result.split('\n\n')
        print(f"\n处理完成！")
        print(f"提取段落总数：{len(paragraphs)}")
        print("\n" + "=" * 50 + " 网页内容 " + "=" * 50)
        print(result)

        # 保存到文件（可选）
        try:
            with open('extracted_content.txt', 'w', encoding='utf-8') as f:
                f.write(result)
            print("\n内容已保存到 extracted_content.txt")
        except Exception as e:
            print(f"\n保存文件时出错：{str(e)}")
    else:
        print("\n" + "=" * 50 + " 错误信息 " + "=" * 50)
        print(result)


main()