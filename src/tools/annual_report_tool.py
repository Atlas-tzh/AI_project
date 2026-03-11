"""
年报文档搜索工具
用于从知识库中检索年报文档信息
"""
from langchain.tools import tool, ToolRuntime
from coze_coding_dev_sdk import KnowledgeClient, Config, KnowledgeDocument, DataSourceType, ChunkConfig
from coze_coding_utils.runtime_ctx.context import new_context
import json
from typing import Optional, List


# 知识库表名
ANNUAL_REPORT_TABLE = "annual_reports"


@tool
def search_annual_report(
    query: str,
    company_name: Optional[str] = None,
    top_k: int = 5,
    min_score: float = 0.6,
    runtime: ToolRuntime = None
) -> str:
    """
    从知识库中搜索年报文档信息
    
    Args:
        query: 搜索查询（如：营收情况、研发投入、市场战略等）
        company_name: 公司名称（可选，用于筛选特定公司的年报）
        top_k: 返回结果数量（默认5）
        min_score: 最小相似度阈值（0-1，默认0.6）
    
    Returns:
        包含年报信息的JSON字符串，包括文档来源和内容片段
    """
    ctx = runtime.context if runtime else new_context(method="search_annual_report")
    client = KnowledgeClient(config=Config(), ctx=ctx)
    
    # 如果指定了公司名称，添加到查询中
    search_query = f"{company_name} {query}" if company_name else query
    
    try:
        # 执行语义搜索
        response = client.search(
            query=search_query,
            table_names=[ANNUAL_REPORT_TABLE],
            top_k=top_k,
            min_score=min_score
        )
        
        result = {
            "query": query,
            "company": company_name,
            "total_results": len(response.chunks) if response.chunks else 0,
            "sources": [],
            "content_snippets": []
        }
        
        if response.chunks:
            for chunk in response.chunks:
                source_info = {
                    "doc_id": chunk.doc_id,
                    "score": round(chunk.score, 4),
                    "content_length": len(chunk.content)
                }
                result["sources"].append(source_info)
                
                # 提取内容片段（限制长度）
                snippet = {
                    "doc_id": chunk.doc_id,
                    "score": round(chunk.score, 4),
                    "content": chunk.content[:800] if len(chunk.content) > 800 else chunk.content
                }
                result["content_snippets"].append(snippet)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"搜索年报文档失败: {str(e)}",
            "query": search_query
        }, ensure_ascii=False, indent=2)


@tool
def import_annual_report(
    company_name: str,
    year: str,
    source_type: str = "text",
    content: Optional[str] = None,
    url: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    导入年报文档到知识库
    
    Args:
        company_name: 公司名称
        year: 年份
        source_type: 来源类型（text=文本内容，url=网页链接）
        content: 文本内容（当source_type为text时使用）
        url: 年报URL链接（当source_type为url时使用）
    
    Returns:
        导入结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="import_annual_report")
    client = KnowledgeClient(config=Config(), ctx=ctx)
    
    try:
        # 创建文档元数据
        metadata = {
            "company_name": company_name,
            "year": year,
            "source_type": source_type
        }
        
        # 创建知识库文档
        if source_type == "text" and content:
            doc = KnowledgeDocument(
                source=DataSourceType.TEXT,
                raw_data=f"{company_name} {year}年度报告\n\n{content}",
                metadata=metadata
            )
        elif source_type == "url" and url:
            doc = KnowledgeDocument(
                source=DataSourceType.URL,
                url=url,
                metadata=metadata
            )
        else:
            return json.dumps({
                "error": "请提供有效的文本内容或URL",
                "company": company_name,
                "year": year
            }, ensure_ascii=False, indent=2)
        
        # 配置分块策略
        chunk_config = ChunkConfig(
            separator="\n\n",
            max_tokens=2000,
            remove_extra_spaces=True
        )
        
        # 导入文档
        response = client.add_documents(
            documents=[doc],
            table_name=ANNUAL_REPORT_TABLE,
            chunk_config=chunk_config
        )
        
        result = {
            "success": response.code == 0,
            "company": company_name,
            "year": year,
            "source_type": source_type,
            "doc_ids": response.doc_ids if response.code == 0 else [],
            "message": response.msg if response.code != 0 else "导入成功"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"导入年报文档失败: {str(e)}",
            "company": company_name,
            "year": year
        }, ensure_ascii=False, indent=2)


@tool
def extract_financial_highlights(
    company_name: str,
    year: str,
    runtime: ToolRuntime = None
) -> str:
    """
    从年报中提取关键财务数据摘要
    
    Args:
        company_name: 公司名称
        year: 年份
    
    Returns:
        关键财务数据JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="extract_financial_highlights")
    client = KnowledgeClient(config=Config(), ctx=ctx)
    
    # 构建多个查询来提取不同类型的财务数据
    queries = [
        f"{company_name} {year} 营收 收入",
        f"{company_name} {year} 净利润 利润",
        f"{company_name} {year} 总资产 资产",
        f"{company_name} {year} 现金流 现金",
        f"{company_name} {year} 研发投入 研发费用"
    ]
    
    result = {
        "company": company_name,
        "year": year,
        "financial_highlights": {},
        "sources": []
    }
    
    try:
        for query in queries:
            response = client.search(
                query=query,
                table_names=[ANNUAL_REPORT_TABLE],
                top_k=3,
                min_score=0.5
            )
            
            if response.chunks:
                for chunk in response.chunks[:1]:  # 只取最相关的一个
                    # 提取关键词作为财务指标类型
                    if "营收" in query or "收入" in query:
                        key = "revenue"
                    elif "净利润" in query or "利润" in query:
                        key = "net_profit"
                    elif "总资产" in query or "资产" in query:
                        key = "total_assets"
                    elif "现金流" in query or "现金" in query:
                        key = "cash_flow"
                    elif "研发" in query:
                        key = "rd_expense"
                    else:
                        key = "other"
                    
                    if key not in result["financial_highlights"]:
                        result["financial_highlights"][key] = []
                    
                    result["financial_highlights"][key].append({
                        "content": chunk.content[:500],
                        "score": round(chunk.score, 4),
                        "doc_id": chunk.doc_id
                    })
                    
                    # 添加来源信息
                    source_info = {
                        "doc_id": chunk.doc_id,
                        "score": round(chunk.score, 4)
                    }
                    if source_info not in result["sources"]:
                        result["sources"].append(source_info)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"提取财务摘要失败: {str(e)}",
            "company": company_name,
            "year": year
        }, ensure_ascii=False, indent=2)


@tool
def search_multiple_reports(
    query: str,
    years: str,
    company_name: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    搜索多个年份的年报数据（用于趋势分析）
    
    Args:
        query: 搜索查询
        years: 年份列表，用逗号分隔（如：2021,2022,2023）
        company_name: 公司名称（可选）
    
    Returns:
        多年度数据JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="search_multiple_reports")
    client = KnowledgeClient(config=Config(), ctx=ctx)
    
    year_list = [y.strip() for y in years.split(",")]
    
    result = {
        "query": query,
        "company": company_name,
        "years": year_list,
        "yearly_data": {},
        "sources": []
    }
    
    try:
        for year in year_list:
            search_query = f"{company_name} {year} {query}" if company_name else f"{year} {query}"
            
            response = client.search(
                query=search_query,
                table_names=[ANNUAL_REPORT_TABLE],
                top_k=3,
                min_score=0.5
            )
            
            if response.chunks:
                result["yearly_data"][year] = []
                
                for chunk in response.chunks:
                    result["yearly_data"][year].append({
                        "content": chunk.content[:500],
                        "score": round(chunk.score, 4),
                        "doc_id": chunk.doc_id
                    })
                    
                    # 记录来源
                    source_info = {
                        "year": year,
                        "doc_id": chunk.doc_id,
                        "score": round(chunk.score, 4)
                    }
                    result["sources"].append(source_info)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"搜索多年报数据失败: {str(e)}",
            "query": query,
            "years": year_list
        }, ensure_ascii=False, indent=2)
