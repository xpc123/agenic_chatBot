#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JedAI LLM 测试脚本

根据 JedAI 官方文档测试 LangChain 集成
"""
import os
import sys
import httpx

# 添加 backend 到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# JedAI 配置
JEDAI_URL = os.environ.get("JEDAI_API_BASE", "http://sjf-dsgdspr-084.cadence.com:5668")


def test_jedai_login():
    """测试 JedAI 登录"""
    print("=" * 60)
    print("测试 1: JedAI 登录")
    print("=" * 60)
    
    username = os.environ.get("JEDAI_USERNAME")
    password = os.environ.get("JEDAI_PASSWORD")
    
    if not username or not password:
        print("❌ 请在 .env 文件中配置 JEDAI_USERNAME 和 JEDAI_PASSWORD")
        return None
    
    print(f"用户名: {username}")
    print(f"JedAI URL: {JEDAI_URL}")
    
    try:
        with httpx.Client(verify=False, timeout=30) as client:
            response = client.post(
                f"{JEDAI_URL}/api/v1/security/login",
                headers={"Content-Type": "application/json"},
                json={
                    "username": username,
                    "password": password,
                    "provider": "LDAP"
                }
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    print(f"✅ 登录成功！Token: {token[:50]}...")
                    return token
                else:
                    print(f"❌ 登录失败: 无 access_token")
                    print(f"Response: {data}")
                    return None
            else:
                print(f"❌ 登录失败: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None


def test_jedai_direct_api(token: str):
    """直接测试 JedAI API（不使用 LangChain）"""
    print("\n" + "=" * 60)
    print("测试 2: 直接调用 JedAI API")
    print("=" * 60)
    
    api_url = f"{JEDAI_URL}/api/copilot/v1/llm/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "accept": "*/*",
        "Authorization": f"Bearer {token}"
    }
    
    # 测试 gcp_oss 模型
    payload = {
        "model": "gcp_oss",
        "messages": [
            {"role": "user", "content": "Hello, what is 2+2?"}
        ],
        "temperature": 0.7,
        "max_tokens": 256,
        # GCP 模型需要的额外参数
        "project": "gcp-cdns-llm-test",
        "location": "us-central1",
        "deployment": "meta/llama-3.3-70b-instruct-maas"
    }
    
    print(f"API URL: {api_url}")
    print(f"Model: gcp_oss -> {payload['deployment']}")
    
    try:
        with httpx.Client(verify=False, timeout=120) as client:
            response = client.post(api_url, headers=headers, json=payload)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"✅ API 调用成功！")
                print(f"Response: {content}")
                return True
            else:
                print(f"❌ API 调用失败: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ API 调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jedai_langchain(token: str):
    """测试 LangChain 集成 JedAI（使用官方推荐方式）"""
    print("\n" + "=" * 60)
    print("测试 3: LangChain 集成 JedAI (官方方式)")
    print("=" * 60)
    
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("❌ langchain_openai 未安装")
        return False
    
    LOCAL_LLM_BASE_URL = f"{JEDAI_URL}/api/copilot/v1/llm"
    LOCAL_LLM_API_KEY = token
    LOCAL_LLM_MODEL_NAME = "gcp_oss"  # 使用 gcp_oss 作为 model name
    
    print(f"Base URL: {LOCAL_LLM_BASE_URL}")
    print(f"Model Name: {LOCAL_LLM_MODEL_NAME}")
    
    try:
        # 根据 JedAI 文档，需要在 extra_body 中传递 GCP 参数
        llm = ChatOpenAI(
            openai_api_base=LOCAL_LLM_BASE_URL,
            openai_api_key=LOCAL_LLM_API_KEY,
            model_name=LOCAL_LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=256,
            http_client=httpx.Client(verify=False),
            extra_body={
                "project": "gcp-cdns-llm-test",
                "location": "us-central1",
                "deployment": "meta/llama-3.3-70b-instruct-maas"
            }
        )
        
        print("LangChain ChatOpenAI 初始化成功")
        print("正在调用 invoke...")
        
        response = llm.invoke("What is 2+2? Answer briefly.")
        
        print(f"✅ LangChain 调用成功！")
        print(f"Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"❌ LangChain 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jedai_on_prem(token: str):
    """测试 On-prem 模型"""
    print("\n" + "=" * 60)
    print("测试 4: On-prem 模型 (Llama3.3)")
    print("=" * 60)
    
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("❌ langchain_openai 未安装")
        return False
    
    LOCAL_LLM_BASE_URL = f"{JEDAI_URL}/api/copilot/v1/llm"
    LOCAL_LLM_API_KEY = token
    LOCAL_LLM_MODEL_NAME = "Llama3.3_JEDAI_MODEL_CHAT_2"  # On-prem 模型直接用模型名
    
    print(f"Base URL: {LOCAL_LLM_BASE_URL}")
    print(f"Model Name: {LOCAL_LLM_MODEL_NAME}")
    
    try:
        llm = ChatOpenAI(
            openai_api_base=LOCAL_LLM_BASE_URL,
            openai_api_key=LOCAL_LLM_API_KEY,
            model_name=LOCAL_LLM_MODEL_NAME,
            temperature=0.7,
            max_tokens=256,
            http_client=httpx.Client(verify=False),
        )
        
        print("LangChain ChatOpenAI 初始化成功")
        print("正在调用 invoke...")
        
        response = llm.invoke("What is 2+2? Answer briefly.")
        
        print(f"✅ On-prem 模型调用成功！")
        print(f"Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"❌ On-prem 模型调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_jedai_claude(token: str):
    """测试 GCP Claude 模型 - 使用 2513 端口"""
    print("\n" + "=" * 60)
    print("测试 5: GCP Claude 模型 (claude-sonnet-4-5)")
    print("=" * 60)
    
    # 根据文档，JedAI 完整服务在 2513 端口 (HTTPS)
    jedai_url_2513 = "https://sjf-dsgdspr-084.cadence.com:2513"
    
    # 首先在 2513 端口登录获取 token
    print("在 2513 端口登录...")
    username = os.environ.get("JEDAI_USERNAME")
    password = os.environ.get("JEDAI_PASSWORD")
    
    try:
        login_response = httpx.post(
            f"{jedai_url_2513}/api/v1/security/login",
            headers={"Content-Type": "application/json"},
            json={"username": username, "password": password, "provider": "LDAP"},
            verify=False,
            timeout=30
        )
        
        if login_response.status_code != 200:
            print(f"❌ 2513 端口登录失败: {login_response.text}")
            return False
            
        token_2513 = login_response.json().get("access_token")
        print(f"✅ 2513 端口登录成功！Token: {token_2513[:50]}...")
        
    except Exception as e:
        print(f"❌ 2513 端口登录异常: {e}")
        return False
    
    # 使用 2513 端口的 token 调用 Claude
    api_url = f"{jedai_url_2513}/api/assistant/v1/llm/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "accept": "*/*",
        "Authorization": f"Bearer {token_2513}"
    }
    
    payload = {
        "model": "GCP_claude-sonnet-4-5",
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer briefly."}
        ],
        "temperature": 0.7,
        "max_tokens": 256,
    }
    
    print(f"API URL: {api_url}")
    print(f"Model: {payload['model']}")
    
    try:
        response = httpx.post(api_url, headers=headers, json=payload, verify=False, timeout=120)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Claude 返回格式: response.json()['content'][0]['text']
            if 'content' in data:
                content = data.get("content", [{}])[0].get("text", "")
            else:
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Claude API 调用成功！")
            print(f"Response: {content}")
            return True
        else:
            print(f"❌ Claude API 调用失败: {response.text[:500]}")
            return False
                
    except Exception as e:
        print(f"❌ Claude 调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_current_llm_client():
    """测试当前项目的 LLM 客户端"""
    print("\n" + "=" * 60)
    print("测试 5: 当前项目 LLMClient")
    print("=" * 60)
    
    try:
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        from app.llm.client import LLMClient
        
        print("正在初始化 LLMClient...")
        client = LLMClient()
        
        print(f"Provider: {client.provider}")
        print(f"Model: {client.model}")
        
        print("正在调用 chat_completion...")
        
        import asyncio
        
        async def test_async():
            response = await client.chat_completion([
                {"role": "user", "content": "What is 2+2? Answer briefly."}
            ])
            return response
        
        response = asyncio.run(test_async())
        
        print(f"✅ LLMClient 调用成功！")
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ LLMClient 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("JedAI LLM 测试")
    print("=" * 60)
    
    # 测试 1: 登录
    token = test_jedai_login()
    if not token:
        print("\n❌ 登录失败，后续测试无法进行")
        return
    
    # 测试 2: 直接 API
    test_jedai_direct_api(token)
    
    # 测试 3: LangChain (gcp_oss)
    test_jedai_langchain(token)
    
    # 测试 4: On-prem 模型
    test_jedai_on_prem(token)
    
    # 测试 5: GCP Claude 模型
    test_jedai_claude(token)
    
    # 测试 6: 项目 LLMClient
    test_current_llm_client()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
