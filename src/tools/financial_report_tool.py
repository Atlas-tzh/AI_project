"""
财报API查询工具
用于从公开财报API和网站获取财务信息
"""
from langchain.tools import tool, ToolRuntime
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.runtime_ctx.context import new_context
import json
from typing import Optional, Dict, Any


@tool
def get_financial_data(
    company_name: str,
    data_type: str = "financial_report",
    year: Optional[str] = None,
    quarter: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    从公开财报源获取公司财务数据
    
    Args:
        company_name: 公司名称（如：腾讯、阿里巴巴、苹果等）
        data_type: 数据类型（financial_report=财报，stock_price=股价，revenue=营收等）
        year: 年份（可选，如：2023）
        quarter: 季度（可选，如：Q1、Q2、Q3、Q4）
    
    Returns:
        包含财务数据的JSON字符串，包括数据来源
    """
    ctx = runtime.context if runtime else new_context(method="get_financial_data")
    client = SearchClient(ctx=ctx)
    
    # 构建搜索查询
    query_parts = [company_name]
    
    if data_type == "financial_report":
        query_parts.append("财报")
    elif data_type == "stock_price":
        query_parts.append("股价")
    elif data_type == "revenue":
        query_parts.append("营收")
    else:
        query_parts.append("财务数据")
    
    if year:
        query_parts.append(year)
    if quarter:
        query_parts.append(quarter)
    
    query = " ".join(query_parts)
    
    try:
        # 使用web搜索获取财报信息
        response = client.web_search_with_summary(
            query=query,
            count=10
        )
        
        # 构建结果数据
        result = {
            "company": company_name,
            "data_type": data_type,
            "year": year,
            "quarter": quarter,
            "sources": [],
            "summary": response.summary if response.summary else "未找到相关摘要",
            "raw_data": []
        }
        
        # 提取来源和数据
        if response.web_items:
            for item in response.web_items[:5]:  # 取前5个结果
                source_info = {
                    "title": item.title,
                    "url": item.url,
                    "site_name": item.site_name,
                    "publish_time": item.publish_time,
                    "snippet": item.snippet,
                    "authority_level": item.auth_info_level,
                    "authority_desc": item.auth_info_des
                }
                result["sources"].append(source_info)
                
                if item.content:
                    result["raw_data"].append({
                        "source": item.title,
                        "content": item.content[:500]  # 限制内容长度
                    })
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"获取财务数据失败: {str(e)}",
            "company": company_name,
            "query": query
        }, ensure_ascii=False, indent=2)


@tool
def search_company_info(
    company_name: str,
    info_type: str = "overview",
    runtime: ToolRuntime = None
) -> str:
    """
    搜索公司基本信息和概况
    
    Args:
        company_name: 公司名称
        info_type: 信息类型（overview=概况，business=业务，management=管理层，competitors=竞争对手）
    
    Returns:
        公司信息JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="search_company_info")
    client = SearchClient(ctx=ctx)
    
    # 根据信息类型构建查询
    query_map = {
        "overview": f"{company_name} 公司概况 简介",
        "business": f"{company_name} 主营业务 业务范围",
        "management": f"{company_name} 管理层 高管团队",
        "competitors": f"{company_name} 竞争对手 行业地位"
    }
    
    query = query_map.get(info_type, f"{company_name} 公司信息")
    
    try:
        response = client.web_search_with_summary(
            query=query,
            count=5
        )
        
        result = {
            "company": company_name,
            "info_type": info_type,
            "summary": response.summary if response.summary else "未找到相关信息",
            "sources": []
        }
        
        if response.web_items:
            for item in response.web_items:
                result["sources"].append({
                    "title": item.title,
                    "url": item.url,
                    "site_name": item.site_name,
                    "snippet": item.snippet,
                    "publish_time": item.publish_time
                })
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"搜索公司信息失败: {str(e)}",
            "company": company_name
        }, ensure_ascii=False, indent=2)


@tool
def compare_financial_data(
    companies: str,
    metric: str = "revenue",
    year: Optional[str] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    比较多家公司的财务指标
    
    Args:
        companies: 公司名称列表，用逗号分隔（如：腾讯,阿里巴巴,字节跳动）
        metric: 比较指标（revenue=营收，profit=利润，market_cap=市值）
        year: 年份（可选）
    
    Returns:
        比较结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="compare_financial_data")
    client = SearchClient(ctx=ctx)
    
    company_list = [c.strip() for c in companies.split(",")]
    
    metric_map = {
        "revenue": "营收",
        "profit": "净利润",
        "market_cap": "市值",
        "pe_ratio": "市盈率"
    }
    
    metric_cn = metric_map.get(metric, metric)
    
    # 构建比较查询
    companies_str = " ".join(company_list)
    query = f"{companies_str} {metric_cn} 对比"
    if year:
        query += f" {year}"
    
    try:
        response = client.web_search_with_summary(
            query=query,
            count=10
        )
        
        result = {
            "companies": company_list,
            "metric": metric,
            "year": year,
            "summary": response.summary if response.summary else "未找到比较数据",
            "sources": [],
            "comparison_data": []
        }
        
        if response.web_items:
            for item in response.web_items[:5]:
                result["sources"].append({
                    "title": item.title,
                    "url": item.url,
                    "site_name": item.site_name,
                    "snippet": item.snippet
                })
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"比较财务数据失败: {str(e)}",
            "companies": company_list
        }, ensure_ascii=False, indent=2)
