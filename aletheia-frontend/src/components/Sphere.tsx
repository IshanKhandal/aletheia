import React, { useEffect, useRef } from 'react';

const Sphere: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let W: number, H: number, DPR: number;
    let rafId: number;

    const resize = () => {
      DPR = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * DPR;
      canvas.height = H * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    };

    window.addEventListener('resize', resize);
    resize();

    const COUNT = 900;
    const pts: any[] = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    
    for (let i = 0; i < COUNT; i++) {
      const y = 1 - (i / (COUNT - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const theta = golden * i;
      pts.push({
        x: Math.cos(theta) * r, y, z: Math.sin(theta) * r,
        s1: Math.random() * Math.PI * 2, s2: Math.random() * Math.PI * 2,
        tw: Math.random() * Math.PI * 2, twSpeed: 0.4 + Math.random() * 0.8,
        size: 0.6 + Math.random() * 1.3
      });
    }

    const bgStars = Array.from({ length: 160 }, () => ({
      x: Math.random(), y: Math.random(), r: Math.random() * 1.1 + 0.2, a: Math.random() * 0.5 + 0.1
    }));

    let t = 0; let rotY = 0;
    let mouseX = 0, mouseY = 0;
    let localMX = -9999, localMY = -9999;
    let hoverStrength = 0;

    const handleMouseMove = (e: MouseEvent) => {
      mouseX = (e.clientX / window.innerWidth - 0.5);
      mouseY = (e.clientY / window.innerHeight - 0.5);
      localMX = e.clientX; localMY = e.clientY;
    };
    const handleMouseLeave = () => { localMX = -9999; localMY = -9999; };

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    const INFLUENCE_R = 190;
    const PUSH = 78;
    const GLOW_BOOST = 1.6;

    const frame = () => {
      t += 0.006; rotY += 0.0016;
      ctx.clearRect(0, 0, W, H);

      const mouseActive = localMX > -1000;
      hoverStrength += ((mouseActive ? 1 : 0) - hoverStrength) * 0.08;

      ctx.save();
      for (const s of bgStars) {
        ctx.globalAlpha = s.a * (0.6 + 0.4 * Math.sin(t * 0.5 + s.x * 10));
        ctx.fillStyle = '#dfe6f5'; 
        ctx.fillRect(s.x * W, s.y * H, s.r, s.r);
      }
      ctx.restore();

      const cx = W / 2 + mouseX * 14; const cy = H / 2 + mouseY * 10;
      const baseR = Math.min(W, H) * 0.30;
      const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
      const tiltX = 0.18 + mouseY * 0.06;
      const cosX = Math.cos(tiltX), sinX = Math.sin(tiltX);

      const projected = [];
      const sparks = [];

      for (const p of pts) {
        const wobble = 1 + 0.06 * Math.sin(t * 1.3 + p.s1) + 0.04 * Math.sin(t * 0.7 + p.s2 + p.x * 3);
        let x = p.x * wobble, y = p.y * wobble, z = p.z * wobble;
        let x1 = x * cosY - z * sinY; let z1 = x * sinY + z * cosY;
        let y1 = y * cosX - z1 * sinX; let z2 = y * sinX + z1 * cosX;
        const persp = 1 / (1 - z2 * 0.32);
        let sx = cx + x1 * baseR * persp; let sy = cy + y1 * baseR * persp;

        const twinkle = 0.4 + 0.6 * Math.abs(Math.sin(t * p.twSpeed + p.tw));
        let a = twinkle * Math.max(0.15, (z2 + 1.3) / 2.4);
        let size = p.size * persp;

        if (hoverStrength > 0.001) {
          const dx = sx - localMX, dy = sy - localMY;
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.0001;
          if (dist < INFLUENCE_R) {
            const proximity = (1 - dist / INFLUENCE_R) * hoverStrength;
            const eased = proximity * proximity;
            sx += (dx / dist) * eased * PUSH; sy += (dy / dist) * eased * PUSH;
            a = Math.min(1, a + eased * GLOW_BOOST);
            size *= 1 + eased * 2.2;
            if (eased > 0.3) sparks.push({ sx, sy, e: eased });
          }
        }
        projected.push({ sx, sy, z: z2, size, a });
      }
      projected.sort((a, b) => a.z - b.z);

      for (const p of projected) {
        ctx.globalAlpha = Math.max(0, Math.min(1, p.a));
        ctx.fillStyle = '#cfe0ff';
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, Math.max(0.4, p.size), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      if (sparks.length && mouseActive) {
        ctx.strokeStyle = '#9db9f2';
        ctx.lineWidth = 0.6;
        for (const s of sparks) {
          ctx.globalAlpha = Math.min(0.5, s.e * 0.6);
          ctx.beginPath();
          ctx.moveTo(localMX, localMY);
          ctx.lineTo(s.sx, s.sy);
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }

      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, baseR * 1.1);
      g.addColorStop(0, 'rgba(120,150,220,0.10)');
      g.addColorStop(1, 'rgba(120,150,220,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      if (hoverStrength > 0.001 && mouseActive) {
        const hg = ctx.createRadialGradient(localMX, localMY, 0, localMX, localMY, INFLUENCE_R);
        hg.addColorStop(0, `rgba(180,205,255,${0.16 * hoverStrength})`);
        hg.addColorStop(1, 'rgba(180,205,255,0)');
        ctx.fillStyle = hg;
        ctx.fillRect(0, 0, W, H);
      }

      rafId = requestAnimationFrame(frame);
    };
    rafId = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return <canvas id="sphere" ref={canvasRef} style={{ position: 'fixed', inset: 0, width: '100vw', height: '100vh', zIndex: -1, pointerEvents: 'none' }} />;
};

export default Sphere;