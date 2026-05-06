import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:5000'

// 获取时间戳图数据
export async function fetchTimestampGraph() {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/graph/timestamp`)
    return response.data
  } catch (error) {
    console.error('获取时间戳图数据失败:', error)
    throw error
  }
}

// 获取快照图数据
export async function fetchSnapshotGraphs() {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/graph/snapshot`)
    return response.data
  } catch (error) {
    console.error('获取快照图数据失败:', error)
    throw error
  }
}

// 上传图表文件
export async function uploadGraphFile(file) {
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  } catch (error) {
    console.error('上传文件失败:', error)
    // 提供更友好的错误信息
    if (error.response) {
      // 服务器返回错误
      throw new Error(error.response.data.message || '服务器处理文件失败')
    } else if (error.request) {
      // 请求发送但没有收到响应
      throw new Error('网络请求失败，请检查后端服务是否启动')
    } else {
      // 其他错误
      throw new Error('上传失败: ' + error.message)
    }
  }
}

// 计算最短路径
export async function calculateShortestPath(sourceId, targetId, mode) {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/shortest-path`, {
      source_id: sourceId,
      target_id: targetId,
      mode: mode
    })
    return response.data
  } catch (error) {
    console.error('计算最短路径失败:', error)
    throw error
  }
}
