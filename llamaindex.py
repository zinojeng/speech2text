@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """使用LlamaIndex搜索知識庫，獲取相關信息。
    
    Args:
        query: 搜索查詢
    
    Returns:
        搜索結果的文本
    """
    try:
        llama_cloud_api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        
        if not llama_cloud_api_key:
            return json.dumps({"error": "請提供Llama Cloud API密鑰"})
            
        index = LlamaCloudIndex(
            name="image-analysis-knowledge-base",
            project_name="圖像分析專案",
            api_key=llama_cloud_api_key,
        )
        
        response = index.as_query_engine().query(query)
        return str(response)
    except Exception as e:
        error_msg = f"搜索知識庫錯誤: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

@mcp.tool()
def extract_text_from_image(image_base64: str) -> str:
    """從圖像中提取純文字內容。
    
    Args:
        image_base64: 圖像的base64編碼字符串
    
    Returns:
        提取的文字內容
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not openai_api_key:
        return json.dumps({"error": "請提供OpenAI API密鑰"})
        
    try:
        client = OpenAI(api_key=openai_api_key)
        
        # 專注於OCR的提示詞
        prompt = """請提取此圖像中的所有文字。只返回圖像中的文字內容，保持原始格式和段落結構。不要添加任何解釋或描述。"""
        
        # 調用OpenAI API
        response = client.chat.completions.create(
            model="gpt-5.6-luna",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=1000
        )
        
        return response.choices[0].message.content
            
    except Exception as e:
        error_type = "文字提取錯誤"
        error_msg = f"{error_type}: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

@mcp.tool()
def image_to_structured_data(image_base64: str, schema: str) -> str:
    """從圖像提取結構化數據，基於提供的schema。
    
    Args:
        image_base64: 圖像的base64編碼字符串
        schema: 描述要提取的結構化數據格式的JSON schema
    
    Returns:
        符合schema的結構化JSON數據
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not openai_api_key:
        return json.dumps({"error": "請提供OpenAI API密鑰"})
        
    try:
        client = OpenAI(api_key=openai_api_key)
        
        # 專注於結構化數據提取的提示詞
        prompt = f"""分析這張圖像並提取符合以下JSON schema的結構化數據:
        
        {schema}
        
        請確保返回的內容是有效的JSON格式，並且符合上述schema。"""
        
        # 調用OpenAI API
        response = client.chat.completions.create(
            model="gpt-5.6-luna",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=1500
        )
        
        return response.choices[0].message.content
            
    except Exception as e:
        error_type = "結構化數據提取錯誤"
        error_msg = f"{error_type}: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

@mcp.tool()
def analyze_document_image_with_llamaparse(image_base64: str) -> str:
    """使用LlamaParse分析文檔圖像，提取結構化信息。
    
    Args:
        image_base64: 文檔圖像的base64編碼字符串
    
    Returns:
        分析結果的文本
    """
    try:
        # 首先將base64圖像保存為臨時文件
        import tempfile
        import base64
        
        llama_cloud_api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        if not llama_cloud_api_key:
            return json.dumps({"error": "請提供Llama Cloud API密鑰"})
        
        # 創建臨時文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(base64.b64decode(image_base64))
        
        # 使用LlamaParse分析
        parser = LlamaParse(
            api_key=llama_cloud_api_key
        )
        
        documents = parser.load_data(temp_file_path)
        
        # 刪除臨時文件
        os.unlink(temp_file_path)
        
        # 返回結構化分析結果
        results = []
        for doc in documents:
            results.append({
                "content": doc.text,
                "metadata": doc.metadata
            })
            
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        error_msg = f"LlamaParse分析文檔圖像錯誤: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

# 主要Streamlit應用界面
def main():
    """主應用程式入口點"""
    st.set_page_config(
        page_title="進階圖像分析工具",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 進階圖像分析與知識提取工具")
    st.write("上傳圖像或文檔進行分析、關鍵詞提取和知識庫搜索")
    
    # 側邊欄設置
    with st.sidebar:
        st.header("API設置")
        
        # API密鑰輸入
        openai_api_key = st.text_input(
            "OpenAI API密鑰",
            type="password",
            value=os.environ.get("OPENAI_API_KEY", ""),
            help="輸入您的OpenAI API密鑰以使用Vision模型"
        )
        
        llama_cloud_api_key = st.text_input(
            "Llama Cloud API密鑰",
            type="password",
            value=os.environ.get("LLAMA_CLOUD_API_KEY", ""),
            help="輸入您的Llama Cloud API密鑰以使用LlamaParse和LlamaIndex"
        )
        
        # 保存API密鑰到環境變數
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            
        if llama_cloud_api_key:
            os.environ["LLAMA_CLOUD_API_KEY"] = llama_cloud_api_key
        
        st.header("分析選項")
        analysis_mode = st.radio(
            "選擇分析模式",
            options=["基本分析", "文字提取", "結構化數據", "文檔分析", "知識庫搜索"],
            help="選擇適合您需求的分析模式"
        )
        
        # 自定義提示詞
        if analysis_mode in ["基本分析", "結構化數據"]:
            custom_prompt = st.text_area(
                "自定義提示詞 (選填)",
                placeholder="輸入自定義提示詞來告訴AI如何分析圖像...",
                help="留空將使用默認提示詞"
            )
        
        # 結構化數據模式的schema輸入
        if analysis_mode == "結構化數據":
            default_schema = """{
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "keywords": {"type": "array", "items": {"type": "string"}},
    "main_objects": {"type": "array", "items": {"type": "string"}},
    "text_content": {"type": "string"}
  }
}"""
            schema_input = st.text_area(
                "JSON Schema",
                value=default_schema,
                help="定義要從圖像提取的結構化數據格式"
            )
        
        # 知識庫搜索的查詢輸入
        if analysis_mode == "知識庫搜索":
            query_input = st.text_input(
                "搜索查詢",
                placeholder="輸入您想搜索的內容...",
                help="基於您的圖像內容自動生成搜索查詢"
            )
    
    # 主區域設置
    upload_col, result_col = st.columns([1, 1])
    
    with upload_col:
        st.subheader("上傳內容")
        
        if analysis_mode == "文檔分析":
            uploaded_files = st.file_uploader(
                "選擇文檔或圖像",
                type=SUPPORTED_FORMATS + ["pdf", "docx", "txt"],
                accept_multiple_files=True,
                help="支援多種文檔和圖像格式"
            )
        else:
            uploaded_files = st.file_uploader(
                "選擇一張或多張圖像",
                type=SUPPORTED_FORMATS,
                accept_multiple_files=True,
                help=f"支援的格式: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        analyze_button_disabled = not uploaded_files or (
            not openai_api_key and analysis_mode in ["基本分析", "文字提取", "結構化數據"]) or (
            not llama_cloud_api_key and analysis_mode in ["文檔分析", "知識庫搜索"])
        
        if st.button("開始分析", disabled=analyze_button_disabled):
            with st.spinner("分析中..."):
                results = {}
                
                for i, uploaded_file in enumerate(uploaded_files):
                    file_name = uploaded_file.name
                    st.write(f"正在處理 {file_name}...")
                    
                    # 讀取上傳的文件
                    file_data = uploaded_file.read()
                    
                    # 處理HEIC格式圖像
                    if file_name.lower().endswith((".heic", ".heif")):
                        try:
                            image = Image.open(io.BytesIO(file_data))
                            buffer = io.BytesIO()
                            image.save(buffer, format="JPEG")
                            file_data = buffer.getvalue()
                        except Exception as e:
                            results[file_name] = {"error": f"轉換HEIC圖像錯誤: {e}"}
                            continue
                    
                    # 將文件數據轉換為base64
                    import base64
                    file_base64 = base64.b64encode(file_data).decode('utf-8')
                    
                    # 根據分析模式調用不同的工具
                    try:
                        if analysis_mode == "基本分析":
                            tool_result = extract_image_keywords(
                                file_base64, 
                                custom_prompt if 'custom_prompt' in locals() else None
                            )
                            # 嘗試解析JSON
                            try:
                                results[file_name] = json.loads(tool_result)
                            except:
                                results[file_name] = {"result": tool_result}
                                
                        elif analysis_mode == "文字提取":
                            tool_result = extract_text_from_image(file_base64)
                            results[file_name] = {"text": tool_result}
                            
                        elif analysis_mode == "結構化數據":
                            tool_result = image_to_structured_data(
                                file_base64, 
                                schema_input if 'schema_input' in locals() else default_schema
                            )
                            # 嘗試解析JSON
                            try:
                                results[file_name] = json.loads(tool_result)
                            except:
                                results[file_name] = {"result": tool_result}
                                
                        elif analysis_mode == "文檔分析":
                            # 如果是PDF等文檔格式，保存為臨時文件
                            if file_name.lower().endswith((".pdf", ".docx", ".txt")):
                                with tempfile.NamedTemporaryFile(suffix=f".{file_name.split('.')[-1]}", delete=False) as temp_file:
                                    temp_file_path = temp_file.name
                                    temp_file.write(file_data)
                                tool_result = analyze_document_with_llama_parse(temp_file_path)
                                os.unlink(temp_file_path)  # 刪除臨時文件
                            else:
                                # 處理圖像文檔
                                tool_result = analyze_document_image_with_llamaparse(file_base64)
                            
                            # 嘗試解析JSON
                            try:
                                results[file_name] = json.loads(tool_result)
                            except:
                                results[file_name] = {"result": tool_result}
                                
                        elif analysis_mode == "知識庫搜索":
                            # 首先提取圖像文字，然後基於文字內容搜索
                            extracted_text = extract_text_from_image(file_base64)
                            
                            # 生成搜索查詢
                            search_query = query_input if query_input else f"關於以下內容的重要信息: {extracted_text[:200]}"
                            
                            # 執行搜索
                            tool_result = search_knowledge_base(search_query)
                            results[file_name] = {
                                "extracted_text": extracted_text,
                                "search_query": search_query,
                                "search_result": tool_result
                            }
                    
                    except Exception as e:
                        error_type = "處理錯誤"
                        error_msg = f"{error_type}: {e}"
                        logger.error(error_msg)
                        results[file_name] = {"error": error_msg}
                
                # 顯示結果
                st.session_state.results = results
    
    # 顯示結果
    with result_col:
        st.subheader("分析結果")
        
        if "results" in st.session_state and st.session_state.results:
            # 創建下載按鈕
            json_results = json.dumps(st.session_state.results, ensure_ascii=False, indent=2)
            st.download_button(
                label="下載完整結果 (JSON)",
                data=json_results,
                file_name="analysis_results.json",
                mime="application/json"
            )
            
            # 顯示每個文件的結果
            for file_name, result in st.session_state.results.items():
                with st.expander(f"文件: {file_name}", expanded=True):
                    if "error" in result:
                        st.error(f"錯誤: {result['error']}")
                        continue
                    
                    # 基於分析模式顯示不同的結果
                    if analysis_mode == "基本分析":
                        # 顯示關鍵詞
                        if "keywords" in result:
                            st.write("**關鍵詞:**")
                            if isinstance(result["keywords"], list):
                                st.write(", ".join(result["keywords"]))
                            else:
                                st.write(result["keywords"])
                        
                        # 顯示描述
                        if "description" in result:
                            st.write("**描述:**")
                            st.write(result["description"])
                        
                        # 顯示其他信息
                        cols = st.columns(2)
                        
                        with cols[0]:
                            if "main_colors" in result:
                                st.write("**主要顏色:**")
                                if isinstance(result["main_colors"], list):
                                    for color in result["main_colors"]:
                                        st.write(f"- {color}")
                                else:
                                    st.write(result["main_colors"])
                        
                        with cols[1]:
                            if "objects" in result:
                                st.write("**識別的物體:**")
                                if isinstance(result["objects"], list):
                                    for obj in result["objects"]:
                                        st.write(f"- {obj}")
                                else:
                                    st.write(result["objects"])
                        
                        # 顯示識別的文字
                        if "text" in result:
                            st.write("**識別的文字:**")
                            st.write(result["text"])
                    
                    elif analysis_mode == "文字提取":
                        st.write("**提取的文字:**")
                        st.write(result.get("text", "無法提取文字"))
                    
                    elif analysis_mode == "結構化數據":
                        # 顯示結構化數據
                        for key, value in result.items():
                            if key != "result" and key != "raw":
                                st.write(f"**{key}:**")
                                if isinstance(value, list):
                                    for item in value:
                                        st.write(f"- {item}")
                                else:
                                    st.write(value)
                    
                    elif analysis_mode == "文檔分析":
                        # 顯示文檔分析結果
                        if isinstance(result, list):
                            for doc_result in result:
                                st.write("**文檔內容:**")
                                st.write(doc_result.get("content", "無內容"))
                                
                                st.write("**元數據:**")
                                for meta_key, meta_value in doc_result.get("metadata", {}).items():
                                    st.write(f"- {meta_key}: {meta_value}")
                        else:
                            st.write(result.get("result", json.dumps(result, ensure_ascii=False)))
                    
                    elif analysis_mode == "知識庫搜索":
                        st.write("**提取的文字:**")
                        st.write(result.get("extracted_text", "無法提取文字"))
                        
                        st.write("**搜索查詢:**")
                        st.write(result.get("search_query", "無搜索查詢"))
                        
                        st.write("**搜索結果:**")
                        st.write(result.get("search_result", "無搜索結果"))
                    
                    # 顯示原始結果
                    with st.expander("查看原始數據"):
                        st.code(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            st.info("上傳內容並點擊分析按鈕以查看結果")

    # 顯示MCP服務器信息
    with st.expander("MCP服務器信息"):
        st.markdown("""
        ### MCP服務器已啟動
        
        本應用整合了以下LlamaMCP工具:
        
        1. **extract_image_keywords** - 使用Vision API提取圖像關鍵詞
        2. **extract_text_from_image** - 從圖像提取純文字
        3. **image_to_structured_data** - 提取符合Schema的結構化數據
        4. **analyze_document_with_llama_parse** - 使用LlamaParse分析文檔
        5. **analyze_document_image_with_llamaparse** - 分析文檔圖像
        6. **search_knowledge_base** - 搜索LlamaIndex知識庫
        
        如需將這些工具連接到Claude Desktop或其他支持MCP的客戶端，請使用以下命令：
        ```
        python mcp-server.py
        ```
        
        詳細配置說明請參考: [LlamaCloud MCP GitHub](https://github.com/run-llama/llamacloud-mcp)
        """)

# 啟動MCP服務器和Streamlit應用
if __name__ == "__main__":
    import threading
    import asyncio
    
    # 啟動MCP服務器
    def run_mcp_server():
        asyncio.run(mcp.run_sse_async())
    
    # 在單獨的線程中啟動MCP服務器
    server_thread = threading.Thread(target=run_mcp_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 啟動Streamlit應用
    main()