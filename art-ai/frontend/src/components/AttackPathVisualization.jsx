import React, { useMemo } from 'react'
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow'
import 'reactflow/dist/style.css'
import './AttackPathVisualization.css'

function AttackPathVisualization({ attackPath, finalAccessLevel }) {
  const { nodes, edges } = useMemo(() => {
    if (!attackPath || attackPath.length === 0) {
      return { nodes: [], edges: [] }
    }

    const nodes = []
    const edges = []

    // Create initial node
    nodes.push({
      id: 'start',
      type: 'input',
      data: { label: 'Start\n(None Access)' },
      position: { x: 100, y: 200 },
      style: { background: '#ff4444', color: '#fff' }
    })

    let currentLevel = 'none'
    let xPosition = 300
    const ySpacing = 150
    const levelYPositions = {
      none: 200,
      public: 100,
      internal: 300,
      admin: 50
    }

    attackPath.forEach((step, index) => {
      const stepId = `step-${index}`
      const isSuccess = step.success
      const newLevel = step.access_level

      // Determine node color based on success and access level
      let nodeColor = '#666'
      if (isSuccess) {
        if (newLevel === 'admin') nodeColor = '#00ff88'
        else if (newLevel === 'internal') nodeColor = '#00aaff'
        else if (newLevel === 'public') nodeColor = '#ffaa00'
        else nodeColor = '#ff4444'
      } else {
        nodeColor = step.blocked ? '#ff0000' : '#666'
      }

      // Calculate Y position based on access level
      const yPos = levelYPositions[newLevel] || 200

      nodes.push({
        id: stepId,
        data: {
          label: (
            <div className="node-content">
              <div className="node-action">{step.action.replace(/_/g, ' ')}</div>
              <div className="node-status">
                {isSuccess ? '✓ Success' : step.blocked ? '✗ Blocked' : '✗ Failed'}
              </div>
              <div className="node-level">Level: {newLevel}</div>
              {step.discovered_component && (
                <div className="node-component">Found: {step.discovered_component}</div>
              )}
            </div>
          )
        },
        position: { x: xPosition, y: yPos },
        style: {
          background: nodeColor,
          color: '#fff',
          border: isSuccess ? '2px solid #00ff88' : '2px solid #666',
          minWidth: 180
        }
      })

      // Create edge from previous node
      const sourceId = index === 0 ? 'start' : `step-${index - 1}`
      edges.push({
        id: `edge-${index}`,
        source: sourceId,
        target: stepId,
        animated: isSuccess,
        style: {
          stroke: isSuccess ? '#00ff88' : '#666',
          strokeWidth: isSuccess ? 2 : 1
        },
        label: `R: ${step.reward?.toFixed(1) || 0}`
      })

      currentLevel = newLevel
      xPosition += 250
    })

    // Add final node
    nodes.push({
      id: 'end',
      type: 'output',
      data: { label: `End\n(${finalAccessLevel} Access)` },
      position: { x: xPosition, y: levelYPositions[finalAccessLevel] || 200 },
      style: {
        background: finalAccessLevel === 'admin' ? '#00ff88' : '#00aaff',
        color: '#fff',
        border: '2px solid #00ff88'
      }
    })

    if (attackPath.length > 0) {
      edges.push({
        id: 'edge-end',
        source: `step-${attackPath.length - 1}`,
        target: 'end',
        animated: true,
        style: { stroke: '#00ff88', strokeWidth: 2 }
      })
    }

    return { nodes, edges }
  }, [attackPath, finalAccessLevel])

  if (nodes.length === 0) {
    return null
  }

  return (
    <div className="attack-path-viz">
      <h3>Attack Path Visualization</h3>
      <div className="flow-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          attributionPosition="bottom-left"
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
      <div className="path-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#00ff88' }}></span>
          <span>Successful Attack</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#666' }}></span>
          <span>Failed Attack</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#ff0000' }}></span>
          <span>Blocked Attack</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ background: '#00aaff' }}></span>
          <span>Access Level Escalation</span>
        </div>
      </div>
    </div>
  )
}

export default AttackPathVisualization

