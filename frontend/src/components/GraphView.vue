<template>
  <div class="graph-view">
    <!-- 悬浮搜索框 -->
    <div class="search-overlay">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="输入节点 ID 搜索" 
        @keyup.enter="handleSearch"
      />
      <button @click="handleSearch">定位</button>
      <button @click="handleReset">重置</button>
    </div>
    <svg ref="svgRef" class="graph-svg"></svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  graphData: {
    type: Object,
    required: true
  }
})

const svgRef = ref(null)
let simulation = null

// 搜索相关状态
const searchQuery = ref('')

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
  d3.select(svgRef.value)
    .append('defs')
    .append('marker')
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
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
</style>

<style scoped>
.graph-view {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.graph-svg {
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.search-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 10px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-overlay input {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  min-width: 150px;
}

.search-overlay button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background-color: #4CAF50;
  color: white;
  cursor: pointer;
  font-size: 12px;
}

.search-overlay button:hover {
  background-color: #45a049;
}

.search-overlay button:nth-child(3) {
  background-color: #f44336;
}

.search-overlay button:nth-child(3):hover {
  background-color: #da190b;
}
</style>
