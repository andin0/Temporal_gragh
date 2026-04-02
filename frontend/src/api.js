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
export async function uploadGraphFile(file, mode) {
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mode', mode)
    
    const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  } catch (error) {
    console.error('上传文件失败:', error)
    throw error
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
