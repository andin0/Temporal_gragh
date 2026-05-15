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
    </div>
    
    <!-- Graph View Container -->
    <div class="graph-view-container">
      <!-- Empty State for Empty Graph Data -->
      <div v-if="graphData && (graphData.nodes.length === 0 || graphData.links.length === 0)" class="empty-graph-state">
        <div class="empty-graph-icon">🔍</div>
        <div class="empty-graph-title">当前时间窗口内无数据</div>
        <div class="empty-graph-description">请调整时间窗口或加载其他数据</div>
      </div>
      
      <svg ref="svgRef" class="graph-svg"></svg>
    </div>
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

const emit = defineEmits(['node-select'])

const svgRef = ref(null)
let simulation = null

const searchQuery = ref('')
const pathSource = ref(null)
const pathTarget = ref(null)
let currentPathNodes = []

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

const uniqueGroups = computed(() => {
  if (!props.graphData || !props.graphData.nodes) return []
  const groups = new Set()
  props.graphData.nodes.forEach(node => {
    groups.add(node.group || 0)
  })
  return Array.from(groups).sort((a, b) => a - b)
})

function getColorForGroup(group) {
  if (!colorScale) return '#D2D2D7'
  return colorScale(group)
}

function isConnected(a, b) {
  return linkedByIndex[`${a.id},${b.id}`] || a.id === b.id
}

function renderGraph() {
  if (!svgRef.value || !props.graphData) return

  if (simulation) {
    simulation.stop()
  }

  d3.select(svgRef.value).selectAll('*').remove()

  let tooltip = d3.select('body').select('.d3-tooltip')
  if (tooltip.empty()) {
    tooltip = d3.select('body')
      .append('div')
      .attr('class', 'd3-tooltip')
  }

  const nodes = JSON.parse(JSON.stringify(props.graphData.nodes))
  const links = JSON.parse(JSON.stringify(props.graphData.links))
  
  currentNodes = nodes
  currentLinks = links

  const linkCounts = {}
  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source
    const targetId = typeof d.target === 'object' ? d.target.id : d.target
    linkCounts[`${sourceId},${targetId}`] = true
  })

  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source
    const targetId = typeof d.target === 'object' ? d.target.id : d.target
    d.isBidirectional = linkCounts[`${targetId},${sourceId}`] === true
  })

  const container = svgRef.value.parentElement
  width = container.clientWidth
  height = container.clientHeight

  d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)

  const defs = d3.select(svgRef.value)
    .append('defs')
    
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
    .attr('fill', '#D2D2D7')
    .style('stroke', 'none')
  
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
    .attr('fill', '#007AFF')
    .style('stroke', 'none')

  const pageranks = nodes.map(d => d.pagerank || 0)
  const minPR = Math.min(...pageranks)
  const maxPR = Math.max(...pageranks)

  const radiusScale = d3.scaleLinear()
    .domain([minPR, maxPR])
    .range([5, 30])

  colorScale = d3.scaleOrdinal()
    .range(['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'])

  linkedByIndex = {}
  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source
    const targetId = typeof d.target === 'object' ? d.target.id : d.target
    linkedByIndex[`${sourceId},${targetId}`] = true
    linkedByIndex[`${targetId},${sourceId}`] = true
  })

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide().radius(d => radiusScale(d.pagerank || 0) + 2))

  d3Zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  d3Svg = d3.select(svgRef.value)
  d3Svg.call(d3Zoom)
  
  d3Svg.on('click', function(event) {
    if (event.target === this) {
      clearShortestPath()
    }
  })

  const g = d3.select(svgRef.value)
    .append('g')

  linkSelection = g.append('g')
    .selectAll('path')
    .data(links)
    .enter()
    .append('path')
    .attr('fill', 'none')
    .attr('stroke', '#D2D2D7')
    .attr('opacity', 0.7)
    .attr('stroke-width', 2)
    .attr('marker-end', 'url(#arrowhead)')
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

  nodeSelection = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', d => radiusScale(d.pagerank || 0))
    .attr('fill', d => colorScale(d.group || 0))
    .attr('stroke', '#FFFFFF')
    .attr('stroke-width', 2)
    .on('mouseover', (event, d) => {
      tooltip
        .style('opacity', 1)
        .html(`节点: ${d.id}<br>度数: ${d.degree}<br>重要度得分: ${(d.pagerank || 0).toFixed(4)}<br>所属社区群组: Group ${d.group || 0}`)

      if (pathSource.value || pathTarget.value || currentPathNodes.length > 0) return

      nodeSelection.style('opacity', (o) => {
        return isConnected(d, o) ? 1 : 0.1
      })

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
      tooltip.style('opacity', 0)

      if (pathSource.value || pathTarget.value || currentPathNodes.length > 0) return

      nodeSelection.style('opacity', 1)

      linkSelection
        .style('opacity', 0.7)
        .style('stroke-width', 2)
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )
    .on('dblclick', (event, d) => {
      d.fx = null
      d.fy = null
      d3.select(event.currentTarget)
        .attr('stroke', null)
        .attr('stroke-width', null)
      simulation.alpha(1).restart()
      emit('node-select', d)
    })
    .on('contextmenu', handleRightClick)

  g.append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text(d => d.id)
    .attr('font-size', 12)
    .attr('dx', 12)
    .attr('dy', 4)

  function calculateShortenedPath(d) {
    const dx = d.target.x - d.source.x;
    const dy = d.target.y - d.source.y;
    const dr = Math.sqrt(dx * dx + dy * dy);
    
    if (dr === 0) return "";
    
    const nodeStrokeWidth = 3;
    const safetyBuffer = 2;
    const targetR = radiusScale(d.target.pagerank || 0) + nodeStrokeWidth + safetyBuffer;
    
    const targetX = d.target.x - (dx * targetR) / dr;
    const targetY = d.target.y - (dy * targetR) / dr;

    return `M${d.source.x},${d.source.y}L${targetX},${targetY}`;
  }

  simulation.on('tick', () => {
    linkSelection.attr('d', calculateShortenedPath)

    nodeSelection
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    g.selectAll('text')
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    d.fx = d.x
    d.fy = d.y
  }

  function dragged(event, d) {
    d.fx = event.x
    d.fy = event.y
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0)
    d.fx = d.x
    d.fy = d.y
    d3.select(event.currentTarget)
      .attr('stroke', '#333')
      .attr('stroke-width', 3)
  }
}

watch(
  () => props.graphData,
  () => {
    nextTick(() => {
      renderGraph()
    })
  },
  { deep: false }
)

onMounted(() => {
  nextTick(() => {
    renderGraph()
  })
})

function handleSearch() {
  if (!searchQuery.value) {
    alert('请输入节点 ID');
    return;
  }

  const targetNode = currentNodes.find(node => node.id === searchQuery.value);
  if (!targetNode) {
    alert('未找到该节点');
    return;
  }

  const scale = 2;
  const x = width / 2 - targetNode.x * scale;
  const y = height / 2 - targetNode.y * scale;

  if (d3Svg && d3Zoom) {
    d3Svg.transition().duration(750)
      .call(d3Zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
  }

  if (nodeSelection && linkSelection) {
    nodeSelection
      .style('opacity', (o) => {
        return isConnected(targetNode, o) ? 1 : 0.1;
      })
      .attr('stroke', (o) => {
        return o.id === targetNode.id ? '#007AFF' : '#FFFFFF';
      })
      .attr('stroke-width', (o) => {
        return o.id === targetNode.id ? 5 : 2;
      })
      .style('filter', (o) => {
        return o.id === targetNode.id ? 'drop-shadow(0 0 12px rgba(0, 122, 255, 0.6))' : 'none';
      });

    linkSelection
      .style('opacity', (o) => {
        return o.source.id === targetNode.id || o.target.id === targetNode.id ? 1 : 0.1;
      })
      .style('stroke-width', (o) => {
        return o.source.id === targetNode.id || o.target.id === targetNode.id ? 3 : 2;
      });
  }
}

function handleReset() {
  searchQuery.value = '';

  if (d3Svg && d3Zoom) {
    d3Svg.transition().duration(750)
      .call(d3Zoom.transform, d3.zoomIdentity);
  }

  if (nodeSelection && linkSelection) {
    nodeSelection
      .style('opacity', 1)
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 2)
      .style('filter', 'none');
    linkSelection
      .style('opacity', 0.7)
      .style('stroke-width', 2);
  }

  clearShortestPath();
}

async function handleRightClick(event, d) {
  event.preventDefault()
  
  if (!pathSource.value) {
    pathSource.value = d
    d3.select(event.currentTarget).attr('stroke', '#007AFF').attr('stroke-width', 4)
    return
  }
  
  if (pathSource.value && !pathTarget.value) {
    pathTarget.value = d
    d3.select(event.currentTarget).attr('stroke', '#007AFF').attr('stroke-width', 4)
    
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/shortest-path', {
        source: pathSource.value.id,
        target: pathTarget.value.id,
        links: props.graphData.links
      })
      currentPathNodes = response.data.path
      renderPathAnimation(currentPathNodes)
    } catch (error) {
      alert(error.response?.data?.error || '路径计算失败')
      clearShortestPath()
    }
  }
}

function clearShortestPath() {
  pathSource.value = null
  pathTarget.value = null
  currentPathNodes = []
  
  if (nodeSelection) {
    nodeSelection
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 2)
      .style('opacity', 1)
  }
  if (linkSelection) {
    linkSelection
      .style('opacity', 0.7)
      .attr('stroke', '#D2D2D7')
      .attr('stroke-width', 2)
      .attr('marker-end', 'url(#arrowhead)')
      .style('stroke-dasharray', 'none')
      .style('animation', 'none')
  }
}

function renderPathAnimation(pathArray) {
  function isLinkInPath(link, path) {
    const sId = typeof link.source === 'object' ? link.source.id : link.source
    const tId = typeof link.target === 'object' ? link.target.id : link.target
    for (let i = 0; i < path.length - 1; i++) {
      if (path[i] === sId && path[i+1] === tId) {
        return true
      }
    }
    return false
  }

  linkSelection
    .style('opacity', d => isLinkInPath(d, pathArray) ? 1 : 0.1)
    .attr('stroke', d => isLinkInPath(d, pathArray) ? '#007AFF' : '#D2D2D7')
    .attr('stroke-width', d => isLinkInPath(d, pathArray) ? 4 : 2)
    .attr('marker-end', d => isLinkInPath(d, pathArray) ? 'url(#arrow-highlight)' : 'url(#arrowhead)')
    .style('stroke-dasharray', d => isLinkInPath(d, pathArray) ? '10, 10' : 'none')
    .style('animation', d => isLinkInPath(d, pathArray) ? 'dash 1s linear infinite' : 'none')

  nodeSelection.style('opacity', d => pathArray.includes(d.id) ? 1 : 0.1)
}

function exportToImage() {
  if (!svgRef.value) return

  const svg = svgRef.value
  
  const svgClone = svg.cloneNode(true)
  
  inlineStyles(svgClone)
  
  const svgString = new XMLSerializer().serializeToString(svgClone)
  
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)
  
  const img = new Image()
  img.onload = function() {
    URL.revokeObjectURL(url)
    
    const scale = window.devicePixelRatio || 2
    
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    canvas.width = svg.clientWidth * scale
    canvas.height = svg.clientHeight * scale
    
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    
    ctx.scale(scale, scale)
    
    ctx.drawImage(img, 0, 0, svg.clientWidth, svg.clientHeight)
    
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

function inlineStyles(element) {
  const elements = element.querySelectorAll('*')
  
  elements.forEach(el => {
    const computedStyle = window.getComputedStyle(el)
    let styleString = ''
    
    for (let i = 0; i < computedStyle.length; i++) {
      const property = computedStyle[i]
      styleString += `${property}: ${computedStyle[property]}; `
    }
    
    el.setAttribute('style', styleString)
  })
}

onUnmounted(() => {
  d3.select('body').selectAll('.d3-tooltip').remove()
})
</script>
<style>
.d3-tooltip {
  position: absolute;
  opacity: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  color: #1D1D1F;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  transform: translateY(10px);
  transition: opacity 0.2s, transform 0.2s;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.toast-message {
  position: absolute;
  top: 40px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  color: #1D1D1F;
  padding: 12px 24px;
  border-radius: 30px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: -0.01em;
  z-index: 2000;
  pointer-events: none;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

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
  background-color: #F5F5F7;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.graph-svg {
  background-color: transparent;
  width: 100%;
  height: 100%;
}

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

.control-group {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  font-size: 14px;
  color: #86868B;
  pointer-events: none;
}

.search-overlay input {
  padding: 8px 12px 8px 32px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  font-size: 13px;
  width: 180px;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  color: #1D1D1F;
  outline: none;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.search-overlay input:focus {
  border-color: #007AFF;
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15);
}

.btn {
  padding: 8px 16px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.btn.primary {
  background-color: #007AFF;
  color: white;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.25);
}
.btn.primary:hover { background-color: #0051D5; transform: translateY(-1px); }

.btn.secondary {
  background-color: rgba(0, 0, 0, 0.05);
  color: #1D1D1F;
}
.btn.secondary:hover { background-color: rgba(0, 0, 0, 0.08); color: #000000; }

.btn.danger {
  background-color: rgba(255, 59, 48, 0.1);
  color: #FF3B30;
  border: 1px solid rgba(255, 59, 48, 0.2);
}
.btn.danger:hover { background-color: rgba(255, 59, 48, 0.15); }

.btn.export {
  background-color: rgba(0, 0, 0, 0.05);
  color: #1D1D1F;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.btn.export:hover {
  background-color: rgba(0, 0, 0, 0.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.path-info {
  display: flex;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  gap: 8px;
}

.path-badge {
  padding: 6px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.path-badge strong { margin-left: 4px; font-weight: 600; }
.path-badge.source { background-color: rgba(52, 199, 89, 0.1); color: #34C759; border: 1px solid rgba(52, 199, 89, 0.2); }
.path-badge.target { background-color: rgba(0, 122, 255, 0.1); color: #007AFF; border: 1px solid rgba(0, 122, 255, 0.2); }
.path-arrow { color: #86868B; display: flex; align-items: center; }

.legend-panel {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  z-index: 999;
  min-width: 200px;
  max-width: 300px;
  color: #1D1D1F;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.legend-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #1D1D1F;
  letter-spacing: -0.02em;
}

.legend-section {
  margin-bottom: 0;
}

.legend-subtitle {
  font-size: 14px;
  font-weight: 500;
  margin: 0 0 8px 0;
  color: #86868B;
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
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.color-label {
  flex: 1;
}

@media (max-width: 768px) {
  .legend-panel {
    bottom: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }
}

.graph-view-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.empty-graph-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
  pointer-events: none;
}

.empty-graph-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.4;
}

.empty-graph-title {
  font-size: 1.2rem;
  color: #1D1D1F;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.empty-graph-description {
  font-size: 0.9rem;
  color: #86868B;
}
</style>