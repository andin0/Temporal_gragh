<template>
  <div class="graph-view">
    <!-- 悬浮搜索框 -->
    <div class="search-overlay">
      <div class="control-group">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="输入节点 ID 搜索..." 
            @keyup.enter="handleSearch"
          />
        </div>
        <button class="btn primary" @click="handleSearch">定位</button>
        <button class="btn secondary" @click="handleReset">重置</button>
        <button class="btn danger" @click="clearShortestPath">清除路径</button>
      </div>
      
      <div v-if="pathSource" class="path-info">
        <div class="path-badge source">📍 起点: <strong>{{ pathSource.id }}</strong></div>
        <div class="path-arrow" v-if="pathTarget">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </div>
        <div class="path-badge target" v-if="pathTarget">🎯 终点: <strong>{{ pathTarget.id }}</strong></div>
      </div>
    </div>
    <svg ref="svgRef" class="graph-svg"></svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import axios from 'axios'

const props = defineProps({
  graphData: {
    type: Object,
    required: true
  },
  mode: {
    type: String,
    default: 'timestamp'
  }
})

const svgRef = ref(null)
let simulation = null

// 搜索相关状态
const searchQuery = ref('')

// 最短路径相关状态
const pathSource = ref(null)
const pathTarget = ref(null)
let currentPathNodes = []

// D3 实例和数据，用于搜索和定位
let d3Zoom = null
let d3Svg = null
let currentNodes = []
let currentLinks = []
let linkedByIndex = {}
let colorScale = null
let nodeSelection = null
let linkSelection = null
let width = 0
let height = 0

// 判定两个节点是否相连（或者是节点自身）
function isConnected(a, b) {
  return linkedByIndex[`${a.id},${b.id}`] || a.id === b.id
}

function renderGraph() {
  if (!svgRef.value || !props.graphData) return

  // 清理旧的动画
  if (simulation) {
    simulation.stop()
  }

  // 清除旧的画布内容
  d3.select(svgRef.value).selectAll('*').remove()

  // 初始化 Tooltip（挂载到 body 上，防止被父容器 overflow 裁切，且完美匹配 pageX/Y）
  let tooltip = d3.select('body').select('.d3-tooltip')
  if (tooltip.empty()) {
    tooltip = d3.select('body')
      .append('div')
      .attr('class', 'd3-tooltip')
  }

  // 对传入的数据进行深拷贝，切断响应式关联
  const nodes = JSON.parse(JSON.stringify(props.graphData.nodes))
  const links = JSON.parse(JSON.stringify(props.graphData.links))
  
  // 存储当前数据
  currentNodes = nodes
  currentLinks = links

  // 统计连线方向，用于判断是否是双向边
  const linkCounts = {}
  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source
    const targetId = typeof d.target === 'object' ? d.target.id : d.target
    linkCounts[`${sourceId},${targetId}`] = true
  })

  // 给每条 link 打上标记
  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source
    const targetId = typeof d.target === 'object' ? d.target.id : d.target
    // 如果存在反向的边，则标记为双向
    d.isBidirectional = linkCounts[`${targetId},${sourceId}`] === true
  })

// 获取 SVG 容器的尺寸
  const container = svgRef.value.parentElement // <--- 加上这一行把丢掉的 container 找回来
  width = container.clientWidth
  height = container.clientHeight

  // 设置 SVG 尺寸
  d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)

  // 创建箭头标记
  const defs = d3.select(svgRef.value)
    .append('defs')
    
  // 默认灰色箭头
  defs.append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('xoverflow', 'visible')
    .append('svg:path')
    .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
    .attr('fill', '#999')
    .style('stroke', 'none')
  
  // 高亮金色箭头（用于最短路径）
  defs.append('marker')
    .attr('id', 'arrow-highlight')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('xoverflow', 'visible')
    .append('svg:path')
    .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
    .attr('fill', '#ffeb3b')
    .style('stroke', 'none')

  // 计算节点度数的最大值和最小值
  const degrees = nodes.map(d => d.degree)
  const minDegree = Math.min(...degrees)
  const maxDegree = Math.max(...degrees)

  // 创建颜色比例尺
  colorScale = d3.scaleLinear()
    .domain([minDegree, maxDegree])
    .range(['#9ed2f6', '#f25f5c']) // 浅蓝到深红

  // 构建邻接关系表
  linkedByIndex = {}
  links.forEach(d => {
    // 注意防错：如果是被 D3 处理过的连线，source/target 会变成对象；如果还没处理，则是字符串 ID。
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source
    const targetId = typeof d.target === 'object' ? d.target.id : d.target
    linkedByIndex[`${sourceId},${targetId}`] = true
    linkedByIndex[`${targetId},${sourceId}`] = true
  })

  // 创建力导向模拟
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))

  // 创建缩放行为
  d3Zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  // 应用缩放行为
  d3Svg = d3.select(svgRef.value)
  d3Svg.call(d3Zoom)
  
  // 背景点击清除路径
  d3Svg.on('click', function(event) {
    // 只有当点击的是 svg 本身，而不是其他元素时，才清除路径
    if (event.target === this) {
      clearShortestPath()
    }
  })

  // 创建一个包含所有元素的组
  const g = d3.select(svgRef.value)
    .append('g')

  // 绘制边
  linkSelection = g.append('g')
    .selectAll('path')
    .data(links)
    .enter()
    .append('path')
    .attr('fill', 'none') // 防止 SVG 默认填充曲线闭合区域
    .attr('stroke', '#999')
    .attr('opacity', 0.6) // 使用整体透明度代替 stroke-opacity，确保箭头也会变暗
    .attr('stroke-width', 3) // 加粗连线，便于触发 hover
    .attr('marker-end', 'url(#arrowhead)')
    // 为连线添加鼠标事件
    .on('mouseover', (event, d) => {
      tooltip
        .style('opacity', 1)
        .html(`发送方: ${d.source.id}<br>接收方: ${d.target.id}<br>时间: ${d.timestamp}`)
    })
    .on('mousemove', (event) => {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', () => {
      tooltip.style('opacity', 0)
    })

  // 绘制节点
  nodeSelection = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', d => Math.max(5, d.degree * 2)) // 根据度数设置半径
    .attr('fill', d => colorScale(d.degree)) // 根据度数设置颜色
    // 为节点添加鼠标事件
    .on('mouseover', (event, d) => {
      // 显示 Tooltip
      tooltip
        .style('opacity', 1)
        .html(`节点: ${d.id}<br>度数: ${d.degree}`)

      // 【核心修复】如果处于寻路模式，立即退出，不执行悬浮高亮逻辑
      if (pathSource.value || pathTarget.value || currentPathNodes.length > 0) return

      // 关联高亮：节点
      nodeSelection.style('opacity', (o) => {
        return isConnected(d, o) ? 1 : 0.1
      })

      // 关联高亮：连线
      linkSelection
        .style('opacity', (o) => {
          return o.source.id === d.id || o.target.id === d.id ? 1 : 0.1
        })
        .style('stroke-width', (o) => {
          return o.source.id === d.id || o.target.id === d.id ? 4 : 3
        })
    })
    .on('mousemove', (event) => {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', () => {
      // 隐藏 Tooltip
      tooltip.style('opacity', 0)

      // 【核心修复】如果处于寻路模式，立即退出，防止恢复透明度破坏跑马灯
      if (pathSource.value || pathTarget.value || currentPathNodes.length > 0) return

      // 恢复所有节点的透明度
      nodeSelection.style('opacity', 1)

      // 恢复所有连线的透明度和线宽
      linkSelection
        .style('opacity', 0.6)
        .style('stroke-width', 3)
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )
    // 双击解除固定
    .on('dblclick', (event, d) => {
      // 解除固定
      d.fx = null
      d.fy = null
      // 移除视觉反馈
      d3.select(event.currentTarget)
        .attr('stroke', null)
        .attr('stroke-width', null)
      // 重启物理引擎
      simulation.alpha(1).restart()
    })
    // 右键点击事件，用于设置起点和终点
    .on('contextmenu', handleRightClick)

  // 添加节点标签
  g.append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text(d => d.id)
    .attr('font-size', 12)
    .attr('dx', 12)
    .attr('dy', 4)

// 更新力导向模拟
  simulation.on('tick', () => {
    linkSelection.attr('d', (d) => {
      if (d.isBidirectional) {
        // 如果是双向边，画平缓的弧线
        const dx = d.target.x - d.source.x
        const dy = d.target.y - d.source.y
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5 // 乘以 1.5 让弧度更平缓优雅
        // 使用节点 ID 比较来决定弯曲方向，确保来回两条线对称分开
        const sweep = d.source.id > d.target.id ? 1 : 0
        return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,${sweep} ${d.target.x},${d.target.y}`
      } else {
        // 如果是单向边，直接画直线，视觉更干净
        return `M${d.source.x},${d.source.y}L${d.target.x},${d.target.y}`
      }
    })

    nodeSelection
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    g.selectAll('text')
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })
  // 拖拽开始
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    d.fx = d.x
    d.fy = d.y
  }

  // 拖拽中
  function dragged(event, d) {
    d.fx = event.x
    d.fy = event.y
  }

  // 拖拽结束
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0)
    // 固定节点在当前位置
    d.fx = d.x
    d.fy = d.y
    // 添加视觉反馈，表示节点已被固定
    d3.select(event.currentTarget)
      .attr('stroke', '#333')
      .attr('stroke-width', 3)
  }
}

// 当 graphData 变化时重新渲染
watch(
  () => props.graphData,
  () => {
    nextTick(() => {
      renderGraph()
    })
  },
  { deep: false }
)

// 当组件挂载后渲染
onMounted(() => {
  nextTick(() => {
    renderGraph()
  })
})

// 处理搜索
function handleSearch() {
  if (!searchQuery.value) {
    alert('请输入节点 ID');
    return;
  }

  // 查找节点
  const targetNode = currentNodes.find(node => node.id === searchQuery.value);
  if (!targetNode) {
    alert('未找到该节点');
    return;
  }

  // 平移与放大
  const scale = 2;
  const x = width / 2 - targetNode.x * scale;
  const y = height / 2 - targetNode.y * scale;

  // 应用过渡动画
  if (d3Svg && d3Zoom) {
    d3Svg.transition().duration(750)
      .call(d3Zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
  }

  // 强制高亮
  if (nodeSelection && linkSelection) {
    // 高亮节点
    nodeSelection.style('opacity', (o) => {
      return isConnected(targetNode, o) ? 1 : 0.1;
    });

    // 高亮连线
    linkSelection
      .style('opacity', (o) => {
        return o.source.id === targetNode.id || o.target.id === targetNode.id ? 1 : 0.1;
      })
      .style('stroke-width', (o) => {
        return o.source.id === targetNode.id || o.target.id === targetNode.id ? 4 : 3;
      });
  }
}

// 处理重置
function handleReset() {
  // 清空搜索框
  searchQuery.value = '';

  // 恢复画布视角
  if (d3Svg && d3Zoom) {
    d3Svg.transition().duration(750)
      .call(d3Zoom.transform, d3.zoomIdentity);
  }

  // 恢复所有节点和连线的默认透明度
  if (nodeSelection && linkSelection) {
    nodeSelection.style('opacity', 1);
    linkSelection
      .style('opacity', 0.6)
      .style('stroke-width', 3);
  }

  // 清除路径
  clearShortestPath();
}

// 处理右键点击事件
async function handleRightClick(event, d) {
  event.preventDefault() // 阻止浏览器默认右键菜单
  
  if (!pathSource.value) {
    // 第一次右键：设置起点
    pathSource.value = d
    d3.select(event.currentTarget).attr('stroke', '#ffeb3b').attr('stroke-width', 4)
    return
  }
  
  if (pathSource.value && !pathTarget.value) {
    // 第二次右键：设置终点并请求路径
    pathTarget.value = d
    d3.select(event.currentTarget).attr('stroke', '#ffeb3b').attr('stroke-width', 4)
    
    try {
      // 补全后端的 http://127.0.0.1:5000 地址，直接跨域打过去
      const response = await axios.post('http://127.0.0.1:5000/api/shortest-path', {
        source: pathSource.value.id,
        target: pathTarget.value.id,
        links: props.graphData.links // 将当前画面的真实连线发给后端
      })
      currentPathNodes = response.data.path
      renderPathAnimation(currentPathNodes)
    } catch (error) {
      alert(error.response?.data?.error || '路径计算失败')
      clearShortestPath()
    }
  }
}

// 清除路径
function clearShortestPath() {
  pathSource.value = null
  pathTarget.value = null
  currentPathNodes = []
  
  if (nodeSelection) {
    nodeSelection
      .attr('stroke', null)
      .attr('stroke-width', null)
      .style('opacity', 1)
  }
  if (linkSelection) {
    linkSelection
      .style('opacity', 0.6)
      .attr('stroke', '#999')
      .attr('stroke-width', 3)
      .attr('marker-end', 'url(#arrowhead)')
      .style('stroke-dasharray', 'none')
      .style('animation', 'none')
  }
}

// 绘制路径动画
  function renderPathAnimation(pathArray) {
    // 判断一条边是否在最短路径序列中
    function isLinkInPath(link, path) {
      const sId = typeof link.source === 'object' ? link.source.id : link.source
      const tId = typeof link.target === 'object' ? link.target.id : link.target
      for (let i = 0; i < path.length - 1; i++) {
        // 【核心修复】严格匹配有向图方向：起点必须是 path[i]，终点必须是 path[i+1]
        if (path[i] === sId && path[i+1] === tId) {
          return true
        }
      }
      return false
    }
    // 变暗无关连线，提亮路径连线并加动画
    linkSelection
      .style('opacity', d => isLinkInPath(d, pathArray) ? 1 : 0.1)
      .attr('stroke', d => isLinkInPath(d, pathArray) ? '#ffeb3b' : '#999')
      .attr('stroke-width', d => isLinkInPath(d, pathArray) ? 5 : 3)
      .attr('marker-end', d => isLinkInPath(d, pathArray) ? 'url(#arrow-highlight)' : 'url(#arrowhead)')
      .style('stroke-dasharray', d => isLinkInPath(d, pathArray) ? '10, 10' : 'none')
      .style('animation', d => isLinkInPath(d, pathArray) ? 'dash 1s linear infinite' : 'none')

    // 变暗无关节点
    nodeSelection.style('opacity', d => pathArray.includes(d.id) ? 1 : 0.1)
  }

// 组件卸载时清理 tooltip
onUnmounted(() => {
  d3.select('body').selectAll('.d3-tooltip').remove()
})
</script>
<style>
.d3-tooltip {
  position: absolute;
  opacity: 0;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  color: #f8fafc;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transform: translateY(10px);
  transition: opacity 0.2s, transform 0.2s;
}

.toast-message {
  position: absolute;
  top: 40px; /* 改为顶部居中更现代 */
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  color: #fff;
  padding: 12px 24px;
  border-radius: 30px; /* 胶囊形状 */
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.5px;
  z-index: 2000;
  pointer-events: none;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
}

/* 跑马灯动画保持 */
@keyframes dash {
  to { stroke-dashoffset: -20; }
}
</style>

<style scoped>
.graph-view {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
  background-color: #f8fafc; /* 更柔和的底层背景色 */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.graph-svg {
  background-color: transparent;
  width: 100%;
  height: 100%;
}

/* 毛玻璃悬浮面板 */
.search-overlay {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  padding: 16px;
  border-radius: 16px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 320px;
}

/* 控制按钮组排版 */
.control-group {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 现代搜索框 */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  font-size: 14px;
  color: #94a3b8;
  pointer-events: none;
}

.search-overlay input {
  padding: 8px 12px 8px 32px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  width: 180px;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  color: #334155;
  outline: none;
}

.search-overlay input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

/* 现代按钮设计 */
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn.primary {
  background-color: #3b82f6;
  color: white;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}
.btn.primary:hover { background-color: #2563eb; transform: translateY(-1px); }

.btn.secondary {
  background-color: #f1f5f9;
  color: #475569;
}
.btn.secondary:hover { background-color: #e2e8f0; color: #0f172a; }

.btn.danger {
  background-color: #fff1f2;
  color: #e11d48;
  border: 1px solid #ffe4e6;
}
.btn.danger:hover { background-color: #ffe4e6; }

/* 优雅的路径状态栏 */
.path-info {
  display: flex;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
  gap: 8px;
}

.path-badge {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.path-badge strong { margin-left: 4px; font-weight: 700; }
.path-badge.source { background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.path-badge.target { background-color: #eff6ff; color: #1e3a8a; border: 1px solid #bfdbfe; }
.path-arrow { color: #94a3b8; display: flex; align-items: center; }
</style>
