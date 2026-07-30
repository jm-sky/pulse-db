#!/usr/bin/env node

/**
 * Script to analyze Chrome DevTools Performance trace
 * Extracts key performance metrics from trace JSON file
 */

import { readFileSync } from 'fs'
import { dirname, join } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const traceFile = process.argv[2] || join(__dirname, '../docs/tmp/Trace-20251202T131105.json')

console.log('📊 Analyzing Chrome DevTools Performance Trace...\n')
console.log(`File: ${traceFile}\n`)

// Read and parse trace file
console.log('Reading trace file...')
const traceData = JSON.parse(readFileSync(traceFile, 'utf-8'))
const events = traceData.traceEvents || []

console.log(`Total events: ${events.length.toLocaleString()}\n`)

// Extract metadata
const metadata = traceData.metadata || {}
const startTime = metadata.startTime || 'unknown'
const duration = metadata.modifications?.initialBreadcrumb?.window?.range || 0

console.log('📅 Trace Information:')
console.log(`  Start Time: ${startTime}`)
console.log(`  Duration: ${(duration / 1000).toFixed(2)}ms (${(duration / 1000000).toFixed(2)}s)\n`)

// Analyze events by category
const eventsByCategory = {}
const eventsByName = {}
const longTasks = []
const jsExecution = []
const layoutEvents = []
const paintEvents = []
const networkEvents = []
const memoryEvents = []

events.forEach(event => {
  const cat = event.cat || 'unknown'
  const name = event.name || 'unknown'
  
  // Count by category
  eventsByCategory[cat] = (eventsByCategory[cat] || 0) + 1
  
  // Count by name
  if (!eventsByName[name]) {
    eventsByName[name] = { count: 0, totalDuration: 0, maxDuration: 0 }
  }
  eventsByName[name].count++
  
  // Calculate duration
  const duration = event.dur || 0
  if (duration > 0) {
    eventsByName[name].totalDuration += duration
    if (duration > eventsByName[name].maxDuration) {
      eventsByName[name].maxDuration = duration
    }
  }
  
  // Long tasks (>50ms)
  if (duration > 50000) {
    longTasks.push({
      name,
      cat,
      duration: duration / 1000, // Convert to ms
      ts: event.ts,
      pid: event.pid,
      tid: event.tid,
    })
  }
  
  // JavaScript execution
  if (cat.includes('v8') || cat.includes('devtools.timeline') && name.includes('RunTask')) {
    if (duration > 0) {
      jsExecution.push({
        name,
        duration: duration / 1000,
        ts: event.ts,
      })
    }
  }
  
  // Layout events
  if (name.includes('Layout') || name.includes('RecalculateStyles') || name.includes('UpdateLayoutTree')) {
    layoutEvents.push({
      name,
      duration: duration / 1000,
      ts: event.ts,
    })
  }
  
  // Paint events
  if (name.includes('Paint') || name.includes('Composite') || name.includes('Draw')) {
    paintEvents.push({
      name,
      duration: duration / 1000,
      ts: event.ts,
    })
  }
  
  // Network events
  if (cat.includes('loading') || name.includes('Resource') || name.includes('XHR') || name.includes('Fetch')) {
    networkEvents.push({
      name,
      duration: duration / 1000,
      ts: event.ts,
      args: event.args,
    })
  }
  
  // Memory events
  if (cat.includes('memory') || name.includes('Memory') || name.includes('GC')) {
    memoryEvents.push({
      name,
      duration: duration / 1000,
      ts: event.ts,
      args: event.args,
    })
  }
})

// Print summary
console.log('📈 Event Categories (Top 10):')
const sortedCategories = Object.entries(eventsByCategory)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 10)

sortedCategories.forEach(([cat, count]) => {
  const percentage = ((count / events.length) * 100).toFixed(2)
  console.log(`  ${cat}: ${count.toLocaleString()} (${percentage}%)`)
})

console.log('\n⏱️  Long Tasks (>50ms):')
if (longTasks.length === 0) {
  console.log('  ✅ No long tasks detected!')
} else {
  console.log(`  ⚠️  Found ${longTasks.length} long tasks:`)
  longTasks
    .sort((a, b) => b.duration - a.duration)
    .slice(0, 20)
    .forEach((task, i) => {
      console.log(`    ${i + 1}. ${task.name} (${task.duration.toFixed(2)}ms) [${task.cat}]`)
    })
  
  const totalLongTaskTime = longTasks.reduce((sum, task) => sum + task.duration, 0)
  console.log(`\n  Total time in long tasks: ${totalLongTaskTime.toFixed(2)}ms`)
}

console.log('\n💻 JavaScript Execution:')
if (jsExecution.length > 0) {
  const totalJsTime = jsExecution.reduce((sum, e) => sum + e.duration, 0)
  const avgJsTime = totalJsTime / jsExecution.length
  const maxJsTime = Math.max(...jsExecution.map(e => e.duration))
  
  console.log(`  Total events: ${jsExecution.length.toLocaleString()}`)
  console.log(`  Total time: ${totalJsTime.toFixed(2)}ms`)
  console.log(`  Average time: ${avgJsTime.toFixed(2)}ms`)
  console.log(`  Max time: ${maxJsTime.toFixed(2)}ms`)
  
  // Top JS tasks
  const topJsTasks = jsExecution
    .sort((a, b) => b.duration - a.duration)
    .slice(0, 10)
  
  console.log('\n  Top 10 longest JS tasks:')
  topJsTasks.forEach((task, i) => {
    console.log(`    ${i + 1}. ${task.name}: ${task.duration.toFixed(2)}ms`)
  })
}

console.log('\n🎨 Layout Events:')
if (layoutEvents.length > 0) {
  const totalLayoutTime = layoutEvents.reduce((sum, e) => sum + e.duration, 0)
  console.log(`  Total events: ${layoutEvents.length.toLocaleString()}`)
  console.log(`  Total time: ${totalLayoutTime.toFixed(2)}ms`)
  
  const layoutByType = {}
  layoutEvents.forEach(e => {
    layoutByType[e.name] = (layoutByType[e.name] || 0) + e.duration
  })
  
  console.log('\n  Layout by type:')
  Object.entries(layoutByType)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([name, time]) => {
      console.log(`    ${name}: ${time.toFixed(2)}ms`)
    })
} else {
  console.log('  No layout events found')
}

console.log('\n🖼️  Paint Events:')
if (paintEvents.length > 0) {
  const totalPaintTime = paintEvents.reduce((sum, e) => sum + e.duration, 0)
  console.log(`  Total events: ${paintEvents.length.toLocaleString()}`)
  console.log(`  Total time: ${totalPaintTime.toFixed(2)}ms`)
  
  const paintByType = {}
  paintEvents.forEach(e => {
    paintByType[e.name] = (paintByType[e.name] || 0) + e.duration
  })
  
  console.log('\n  Paint by type:')
  Object.entries(paintByType)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([name, time]) => {
      console.log(`    ${name}: ${time.toFixed(2)}ms`)
    })
} else {
  console.log('  No paint events found')
}

console.log('\n🌐 Network Events:')
if (networkEvents.length > 0) {
  console.log(`  Total events: ${networkEvents.length.toLocaleString()}`)
  
  const slowRequests = networkEvents
    .filter(e => e.duration > 100)
    .sort((a, b) => b.duration - a.duration)
    .slice(0, 10)
  
  if (slowRequests.length > 0) {
    console.log('\n  Slowest requests (>100ms):')
    slowRequests.forEach((req, i) => {
      const url = req.args?.url || req.args?.name || 'unknown'
      console.log(`    ${i + 1}. ${req.name}: ${req.duration.toFixed(2)}ms`)
      console.log(`       URL: ${url.substring(0, 80)}...`)
    })
  }
} else {
  console.log('  No network events found')
}

console.log('\n💾 Memory Events:')
if (memoryEvents.length > 0) {
  console.log(`  Total events: ${memoryEvents.length.toLocaleString()}`)
  
  memoryEvents.slice(0, 10).forEach((event, i) => {
    console.log(`    ${i + 1}. ${event.name}`)
    if (event.args) {
      Object.entries(event.args).slice(0, 3).forEach(([key, value]) => {
        console.log(`       ${key}: ${value}`)
      })
    }
  })
} else {
  console.log('  No memory events found')
}

// Vue-specific analysis
console.log('\n⚡ Vue/React Analysis:')
const vueEvents = events.filter(e => 
  e.name?.includes('Vue') || 
  e.name?.includes('vue') || 
  e.name?.includes('render') ||
  e.name?.includes('update') ||
  e.cat?.includes('v8') && e.name?.includes('FunctionCall')
)

if (vueEvents.length > 0) {
  console.log(`  Found ${vueEvents.length.toLocaleString()} potential Vue/React events`)
  
  const vueByType = {}
  vueEvents.forEach(e => {
    const name = e.name || 'unknown'
    vueByType[name] = (vueByType[name] || 0) + 1
  })
  
  console.log('\n  Top Vue/React event types:')
  Object.entries(vueByType)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([name, count]) => {
      console.log(`    ${name}: ${count.toLocaleString()}`)
    })
} else {
  console.log('  No Vue/React-specific events found')
}

// Performance recommendations
console.log('\n💡 Performance Recommendations:')
const recommendations = []

if (longTasks.length > 10) {
  recommendations.push(`⚠️  Found ${longTasks.length} long tasks - consider code splitting or optimizing heavy computations`)
}

if (jsExecution.length > 1000) {
  recommendations.push(`⚠️  High number of JS execution events (${jsExecution.length}) - check for unnecessary re-renders`)
}

if (layoutEvents.length > 100) {
  recommendations.push(`⚠️  High number of layout events (${layoutEvents.length}) - check for forced reflows`)
}

if (paintEvents.length > 50) {
  recommendations.push(`⚠️  High number of paint events (${paintEvents.length}) - consider using CSS transforms instead of position changes`)
}

if (recommendations.length === 0) {
  console.log('  ✅ No major performance issues detected!')
} else {
  recommendations.forEach(rec => console.log(`  ${rec}`))
}

console.log('\n✅ Analysis complete!\n')

