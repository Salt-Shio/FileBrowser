<template>
  <canvas 
    ref="canvasRef" 
    class="fixed inset-0 pointer-events-none z-[9999]"
  ></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';

// ==========================================
// ⚡ 閃電特效參數設定區
// ==========================================
const CONFIG = {
  // 基本設定
  maxAge: 25,             // 閃電存活時間 (幀數)。數值越大，軌跡越長、消失越慢
  glowColor: 'rgba(255, 255, 255, 0.8)', // 閃電發光顏色
  glowBlur: 25,            // 閃電發光範圍。數值越大光暈越明顯
  
  // 主軌跡設定 (滑鼠連線)
  mainSegmentLength: 20,   // 主軌跡每段折線的平均長度。數值越小，折線越密集
  mainNoise: 10,          // 主軌跡的抖動幅度。數值越大，閃電越扭曲
  
  // 樹狀分岔設定
  branchChance: 0.3,     // 產生第一層分岔的機率 (0.0 ~ 1.0)
  subBranchChance: 0.1,   // 分岔再產生次級分岔的機率
  branchSegmentLength: 8, // 分岔線條每段折線的長度
  branchNoise: 10,        // 分岔線條的抖動幅度
  branchLengthMin: 30,    // 分岔線條的最短長度
  branchLengthMax: 80,    // 分岔線條的最長長度
};
// ==========================================

const canvasRef = ref<HTMLCanvasElement | null>(null);
let ctx: CanvasRenderingContext2D | null = null;
let animationFrameId: number;

interface Point {
  x: number;
  y: number;
  age: number;
}

const points: Point[] = [];

// 繪製樹狀分岔
const drawBranch = (ctx: CanvasRenderingContext2D, startX: number, startY: number, angle: number, length: number, depth: number, opacity: number) => {
  if (depth === 0 || length < 5) return;
  
  const endX = startX + Math.cos(angle) * length;
  const endY = startY + Math.sin(angle) * length;
  
  const dx = endX - startX;
  const dy = endY - startY;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const segments = Math.max(1, Math.floor(dist / CONFIG.branchSegmentLength));
  
  const perpX = -dy / dist;
  const perpY = dx / dist;

  ctx.beginPath();
  ctx.moveTo(startX, startY);

  for (let j = 1; j <= segments; j++) {
    const t = j / segments;
    let nx = startX + dx * t;
    let ny = startY + dy * t;
    
    if (j !== segments) {
      const noise = (Math.random() - 0.5) * CONFIG.branchNoise;
      nx += perpX * noise;
      ny += perpY * noise;
    }
    
    ctx.lineTo(nx, ny);

    // 隨機再次分岔
    if (j !== segments && Math.random() < CONFIG.subBranchChance) {
      const newAngle = angle + (Math.random() - 0.5) * 1.0;
      // 這裡簡化實作
    }
  }

  ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
  ctx.lineWidth = depth * 0.6;
  ctx.stroke();
};

// 遞迴繪製樹狀分岔
const drawBranchRecursive = (ctx: CanvasRenderingContext2D, startX: number, startY: number, angle: number, length: number, depth: number, opacity: number) => {
  if (depth === 0 || length < 5) return;
  
  const endX = startX + Math.cos(angle) * length;
  const endY = startY + Math.sin(angle) * length;
  
  const dx = endX - startX;
  const dy = endY - startY;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const segments = Math.max(1, Math.floor(dist / CONFIG.branchSegmentLength));
  
  const perpX = -dy / dist;
  const perpY = dx / dist;

  ctx.beginPath();
  ctx.moveTo(startX, startY);
  
  const childBranches = [];

  for (let j = 1; j <= segments; j++) {
    const t = j / segments;
    let nx = startX + dx * t;
    let ny = startY + dy * t;
    
    if (j !== segments) {
      const noise = (Math.random() - 0.5) * CONFIG.branchNoise;
      nx += perpX * noise;
      ny += perpY * noise;
      
      if (Math.random() < CONFIG.subBranchChance) {
        const newAngle = angle + (Math.random() - 0.5) * 1.5;
        childBranches.push({x: nx, y: ny, angle: newAngle});
      }
    }
    
    ctx.lineTo(nx, ny);
  }

  ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
  ctx.lineWidth = depth * 0.6;
  ctx.stroke();
  
  childBranches.forEach(b => {
    drawBranchRecursive(ctx, b.x, b.y, b.angle, length * 0.6, depth - 1, opacity * 0.7);
  });
};

// 更新 Canvas 尺寸
const resizeCanvas = () => {
  if (!canvasRef.value) return;
  canvasRef.value.width = window.innerWidth;
  canvasRef.value.height = window.innerHeight;
};

// 記錄滑鼠位置
const handleMouseMove = (e: MouseEvent) => {
  points.push({ x: e.clientX, y: e.clientY, age: 0 });
};

// 繪製閃電特效
const drawLightning = () => {
  if (!canvasRef.value || !ctx) return;
  
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height);

  // 更新每個點的年齡
  for (let i = points.length - 1; i >= 0; i--) {
    points[i].age += 1;
    if (points[i].age > CONFIG.maxAge) {
      points.splice(i, 1);
    }
  }

  if (points.length < 2) {
    animationFrameId = requestAnimationFrame(drawLightning);
    return;
  }

  ctx.lineCap = 'round';
  ctx.lineJoin = 'miter';
  ctx.shadowColor = CONFIG.glowColor;
  ctx.shadowBlur = CONFIG.glowBlur;

  const branchesToDraw: {x: number, y: number, angle: number, length: number, opacity: number, depth: number}[] = [];

  for (let i = 1; i < points.length; i++) {
    const p1 = points[i - 1];
    const p2 = points[i];
    
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    // 距離太短就不需要做太複雜的鋸齒
    if (dist < 1) continue;

    // 根據距離決定要切成幾段閃電折線
    const segments = Math.max(1, Math.floor(dist / CONFIG.mainSegmentLength));
    const perpX = -dy / dist;
    const perpY = dx / dist;

    // 年齡越大，透明度越低
    const opacity = Math.max(0, 1 - (p2.age / CONFIG.maxAge));
    ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`;
    
    // 閃電越新越粗
    ctx.lineWidth = 1.5 + (1 - opacity) * 2;

    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);

    for (let j = 1; j <= segments; j++) {
      const t = j / segments;
      let nx = p1.x + dx * t;
      let ny = p1.y + dy * t;
      
      // 除最後一個點外，加上隨機法向位移 (抖動)
      if (j !== segments) {
        // 隨機產生偏移，營造閃電感
        const noise = (Math.random() - 0.5) * CONFIG.mainNoise;
        nx += perpX * noise;
        ny += perpY * noise;
        
        // 隨機產生樹狀分岔
        if (Math.random() < CONFIG.branchChance) {
          const mainAngle = Math.atan2(dy, dx);
          // 加上 Math.PI (180度) 讓分支往反方向長
          const branchAngle = mainAngle + Math.PI + (Math.random() - 0.5) * 1.0;
          const branchLength = CONFIG.branchLengthMin + Math.random() * (CONFIG.branchLengthMax - CONFIG.branchLengthMin);
          branchesToDraw.push({
            x: nx, y: ny, 
            angle: branchAngle, 
            length: branchLength, 
            opacity: opacity * 0.8, 
            depth: 2
          });
        }
      }
      
      ctx.lineTo(nx, ny);
    }
    ctx.stroke();
  }

  // 畫出所有樹狀分岔
  branchesToDraw.forEach(b => {
    drawBranchRecursive(ctx!, b.x, b.y, b.angle, b.length, b.depth, b.opacity);
  });

  animationFrameId = requestAnimationFrame(drawLightning);
};

onMounted(() => {
  if (canvasRef.value) {
    ctx = canvasRef.value.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    window.addEventListener('mousemove', handleMouseMove);
    drawLightning();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas);
  window.removeEventListener('mousemove', handleMouseMove);
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
});
</script>
