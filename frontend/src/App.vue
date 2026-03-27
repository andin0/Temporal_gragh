<template>
  <div class="app">
    <header class="control-bar">
      <h1>时序图可视化</h1>
      <div class="buttons">
        <button @click="loadTimestampGraph">加载时间戳图</button>
        <button @click="loadSnapshotGraph(0)">加载快照 1</button>
      </div>
    </header>
    <main class="graph-container">
      <GraphView v-if="graphData" :graphData="graphData" />
      <div v-else class="loading">点击上方按钮加载图表</div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import GraphView from './components/GraphView.vue'
import { fetchTimestampGraph, fetchSnapshotGraphs } from './api.js'

const graphData = ref(null)

async function loadTimestampGraph() {
  try {
    const data = await fetchTimestampGraph()
    graphData.value = data
  } catch (error) {
    console.error('加载时间戳图失败:', error)
  }
}

async function loadSnapshotGraph(index) {
  try {
    const snapshots = await fetchSnapshotGraphs()
    if (snapshots[index]) {
      graphData.value = {
        nodes: snapshots[index].nodes,
        links: snapshots[index].links
      }
    }
  } catch (error) {
    console.error('加载快照图失败:', error)
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
}

.control-bar {
  background-color: #333;
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.control-bar h1 {
  font-size: 1.5rem;
}

.buttons button {
  margin-left: 1rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background-color: #4CAF50;
  color: white;
  cursor: pointer;
  font-size: 1rem;
}

.buttons button:hover {
  background-color: #45a049;
}

.graph-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}

.loading {
  font-size: 1.2rem;
  color: #666;
}
</style>
