/**
 * API配置文件
 * 包含API基础URL和AI问答功能所需的API参数
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL
  baseURL: (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, ''),
}

export const aiChatConfig = {
  // OpenAI API地址
  // 前端只请求本项目后端，由后端连接供应商。
  apiEndpoint: `${apiConfig.baseURL}/api/ai/chat`,
  
  // API Key (由开发人员指定)
  // 密钥仅在后端配置，此接口只查询服务是否就绪。
  configEndpoint: `${apiConfig.baseURL}/api/ai/config`,
  
  // 使用的模型
  // 模型由后端选择，浏览器无需提交模型参数。
}
