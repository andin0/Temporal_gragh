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
