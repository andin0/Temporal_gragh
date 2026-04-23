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
        <button class="btn export" @click="exportToImage">📸 导出图片</button>
      </div>
      
      <div v-if="pathSource" class="path-info">
        <div class="path-badge source">📍 起点: <strong>{{ pathSource.id }}</strong></div>
        <div class="path-arrow" v-if="pathTarget">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </div>
        <div class="path-badge target" v-if="pathTarget">🎯 终点: <strong>{{ pathTarget.id }}</strong></div>
      </div>
    </div>
    
    <!-- 动态图例面板 -->
    <div class="legend-panel" v-if="graphData">
      <h3 class="legend-title">图例说明</h3>
      
      <!-- 颜色图例 (社区团伙) -->
      <div class="legend-section">
        <h4 class="legend-subtitle">社区团伙</h4>
        <div class="color-legend">
          <div 
            v-for="group in uniqueGroups" 
            :key="group"
            class="color-item"
          >
            <div 
              class="color-dot" 
              :style="{ backgroundColor: getColorForGroup(group) }"
            ></div>
            <span class="color-label">团伙 Group {{ group }}</span>
          </div>
        </div>
      </div>
      
      <!-- 大小图例 (PageRank) -->
      <div class="legend-section">
        <h4 class="legend-subtitle">核心程度</h4>
        <div class="size-legend">
          <div 
            class="size-item"
            @mouseenter="handleLegendHover('low')"
            @mouseleave="handleLegendLeave"
          >
            <div 
              class="size-circle" 
              :style="{ width: sizeMin + 'px', height: sizeMin + 'px' }"
            ></div>
            <span class="size-label">边缘节点</span>
            <span class="size-value">{{ pagerankMin.toFixed(4) }}</span>
          </div>
          <div 
            class="size-item"
            @mouseenter="handleLegendHover('medium')"
            @mouseleave="handleLegendLeave"
          >
            <div 
              class="size-circle" 
              :style="{ width: sizeMed + 'px', height: sizeMed + 'px' }"
            ></div>
            <span class="size-label">常规节点</span>
            <span class="size-value">{{ pagerankMed.toFixed(4) }}</span>
          </div>
          <div 
            class="size-item"
            @mouseenter="handleLegendHover('high')"
            @mouseleave="handleLegendLeave"
          >
            <div 
              class="size-circle" 
              :style="{ width: sizeMax + 'px', height: sizeMax + 'px' }"
            ></div>
            <span class="size-label">核心枢纽</span>
            <span class="size-value">{{ pagerankMax.toFixed(4) }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <svg ref="svgRef" class="graph-svg"></svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
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

// 图例相关状态
let radiusScale = null

// 计算唯一的社区组
const uniqueGroups = computed(() => {
  if (!props.graphData || !props.graphData.nodes) return []
  const groups = new Set()
  props.graphData.nodes.forEach(node => {
    groups.add(node.group || 0)
  })
  return Array.from(groups).sort((a, b) => a - b)
})

// 计算 PageRank 相关值
const pagerankValues = computed(() => {
  if (!props.graphData || !props.graphData.nodes) return []
  return props.graphData.nodes.map(node => node.pagerank || 0)
})

const pagerankMin = computed(() => {
  const values = pagerankValues.value
  return values.length > 0 ? Math.min(...values) : 0
})

const pagerankMax = computed(() => {
  const values = pagerankValues.value
  return values.length > 0 ? Math.max(...values) : 1
})

const pagerankMed = computed(() => {
  const values = pagerankValues.value
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
})

// 计算大小图例的尺寸
const sizeMin = computed(() => {
  if (!radiusScale) return 10
  return radiusScale(pagerankMin.value) * 2
})

const sizeMed = computed(() => {
  if (!radiusScale) return 20
  return radiusScale(pagerankMed.value) * 2
})

const sizeMax = computed(() => {
  if (!radiusScale) return 30
  return radiusScale(pagerankMax.value) * 2
})

// 计算 PageRank 区间边界
const pagerankRange = computed(() => {
  return pagerankMax.value - pagerankMin.value
})

const pagerankLowBound = computed(() => {
  return pagerankMin.value + pagerankRange.value / 3
})

const pagerankMediumBound = computed(() => {
  return pagerankMin.value + (pagerankRange.value * 2) / 3
})

// 获取组的颜色
function getColorForGroup(group) {
  if (!colorScale) return '#999'
  return colorScale(group)
}

// 处理图例悬停
function handleLegendHover(interval) {
  // 如果有最短路径活动，不进行高亮
  if (pathSource.value || pathTarget.value || currentPathNodes.length > 0) return
  
  if (!nodeSelection || !linkSelection) return
  
  // 确定节点是否在指定区间
  function isInInterval(node) {
    const pr = node.pagerank || 0
    switch (interval) {
      case 'low':
        return pr <= pagerankLowBound.value
      case 'medium':
        return pr > pagerankLowBound.value && pr <= pagerankMediumBound.value
      case 'high':
        return pr > pagerankMediumBound.value
      default:
        return false
    }
  }
  
  // 高亮节点
  nodeSelection
    .transition()
    .duration(300)
    .style('opacity', d => isInInterval(d) ? 1 : 0.1)
    .style('stroke', d => isInInterval(d) ? '#00f2fe' : 'none')
    .style('stroke-width', d => isInInterval(d) ? 2 : 0)
    .style('filter', d => isInInterval(d) ? 'drop-shadow(0 0 8px #00f2fe)' : 'none')
  
  // 高亮关联连线
  linkSelection
    .transition()
    .duration(300)
    .style('opacity', d => {
      const sourceIn = isInInterval(d.source)
      const targetIn = isInInterval(d.target)
      return (sourceIn || targetIn) ? 1 : 0.1
    })
    .style('stroke-width', d => {
      const sourceIn = isInInterval(d.source)
      const targetIn = isInInterval(d.target)
      return (sourceIn || targetIn) ? 4 : 2
    })
}

// 处理图例离开
function handleLegendLeave() {
  // 如果有最短路径活动，不进行重置
  if (pathSource.value || pathTarget.value || currentPathNodes.length > 0) return
  
  if (!nodeSelection || !linkSelection) return
  
  // 重置节点
  nodeSelection
    .transition()
    .duration(300)
    .style('opacity', 1)
    .style('stroke', null)
    .style('stroke-width', null)
    .style('filter', 'none')
  
  // 重置连线
  linkSelection
    .transition()
    .duration(300)
    .style('opacity', 0.6)
    .style('stroke-width', 3)
}

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
    .attr('refX', 9)
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
    .attr('refX', 9)
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

  // 计算PageRank的最大值和最小值
  const pageranks = nodes.map(d => d.pagerank || 0)
  const minPR = Math.min(...pageranks)
  const maxPR = Math.max(...pageranks)

  // 创建半径比例尺（映射PageRank）
  const radiusScale = d3.scaleLinear()
    .domain([minPR, maxPR])
    .range([5, 30])

  // 创建颜色比例尺（映射社区）
  colorScale = d3.scaleOrdinal(d3.schemeSet2)

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
    .force('collide', d3.forceCollide().radius(d => radiusScale(d.pagerank || 0) + 2))

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
    .attr('r', d => radiusScale(d.pagerank || 0)) // 根据PageRank设置半径
    .attr('fill', d => colorScale(d.group || 0)) // 根据社区设置颜色
    // 为节点添加鼠标事件
    .on('mouseover', (event, d) => {
      // 显示 Tooltip
      tooltip
        .style('opacity', 1)
        .html(`节点: ${d.id}<br>度数: ${d.degree}<br>重要度得分: ${(d.pagerank || 0).toFixed(4)}<br>所属社区群组: Group ${d.group || 0}`)

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

  // 动态路径计算函数：确保连线和箭头停在目标节点边缘（仅直线渲染）
  function calculateShortenedPath(d) {
    const dx = d.target.x - d.source.x;
    const dy = d.target.y - d.source.y;
    const dr = Math.sqrt(dx * dx + dy * dy);
    
    if (dr === 0) return "";
    
    // 获取目标节点当前的动态半径，并加上节点描边厚度和安全缓冲量
    const nodeStrokeWidth = 3; // 节点描边宽度
    const safetyBuffer = 2; // 安全缓冲量
    const targetR = radiusScale(d.target.pagerank || 0) + nodeStrokeWidth + safetyBuffer;
    
    // 利用相似三角形/向量原理，计算刚好停在节点边缘的终点坐标
    const targetX = d.target.x - (dx * targetR) / dr;
    const targetY = d.target.y - (dy * targetR) / dr;

    // 所有边统一使用直线渲染
    return `M${d.source.x},${d.source.y}L${targetX},${targetY}`;
  }

// 更新力导向模拟
  simulation.on('tick', () => {
    linkSelection.attr('d', calculateShortenedPath)

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

// 导出为图片
function exportToImage() {
  if (!svgRef.value) return

  // 获取 SVG 元素
  const svg = svgRef.value
  
  // 克隆 SVG 以便进行样式内联化处理
  const svgClone = svg.cloneNode(true)
  
  // 内联所有计算样式
  inlineStyles(svgClone)
  
  // 将 SVG 转换为字符串
  const svgString = new XMLSerializer().serializeToString(svgClone)
  
  // 创建 SVG Blob
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)
  
  // 创建图像对象
  const img = new Image()
  img.onload = function() {
    // 清理 URL
    URL.revokeObjectURL(url)
    
    // 获取设备像素比
    const scale = window.devicePixelRatio || 2
    
    // 创建高清 Canvas
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    // 设置 Canvas 尺寸（考虑缩放）
    canvas.width = svg.clientWidth * scale
    canvas.height = svg.clientHeight * scale
    
    // 设置 Canvas 背景为白色
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    
    // 缩放 Canvas 上下文
    ctx.scale(scale, scale)
    
    // 绘制图像
    ctx.drawImage(img, 0, 0, svg.clientWidth, svg.clientHeight)
    
    // 转换为 PNG 并下载
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const filename = `network_graph_${timestamp}.png`
    
    canvas.toBlob(function(blob) {
      if (blob) {
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = filename
        link.click()
        URL.revokeObjectURL(link.href)
      }
    }, 'image/png')
  }
  
  img.src = url
}

// 内联样式函数
function inlineStyles(element) {
  // 获取所有子元素
  const elements = element.querySelectorAll('*')
  
  // 为每个元素内联计算样式
  elements.forEach(el => {
    const computedStyle = window.getComputedStyle(el)
    let styleString = ''
    
    // 复制所有计算样式
    for (let i = 0; i < computedStyle.length; i++) {
      const property = computedStyle[i]
      styleString += `${property}: ${computedStyle[property]}; `
    }
    
    // 设置内联样式
    el.setAttribute('style', styleString)
  })
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

.btn.export {
  background-color: rgba(0, 30, 60, 0.8);
  color: #00f2fe;
  border: 1px solid #00f2fe;
  box-shadow: 0 2px 4px rgba(0, 242, 254, 0.3);
}

.btn.export:hover {
  background-color: rgba(0, 242, 254, 0.1);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.6);
  transform: translateY(-1px);
}

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

/* 动态图例面板 */
.legend-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 10px 25px -5px rgba(0, 242, 254, 0.2), 0 8px 10px -6px rgba(0, 242, 254, 0.1);
  z-index: 999;
  min-width: 200px;
  max-width: 300px;
  color: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.legend-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 12px 0;
  color: #00f2fe;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}

.legend-section {
  margin-bottom: 16px;
}

.legend-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #94a3b8;
}

.color-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.color-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.color-label {
  flex: 1;
}

.size-legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.size-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.size-circle {
  border: 2px solid #00f2fe;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 242, 254, 0.1);
}

.size-label {
  flex: 1;
}

.size-value {
  color: #00f2fe;
  font-family: monospace;
  font-size: 11px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .legend-panel {
    bottom: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }
}
</style>
