import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { isWebGLAvailable } from '../../utils/webgl';

function SpectrogramGrid3D({ data }: { data?: number[][] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  // Default to 16x32 grid if no data provided
  const rows = data ? data.length : 24;
  const cols = data && data[0] ? data[0].length : 36;
  const count = rows * cols;

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colors = useMemo(() => new Float32Array(count * 3), [count]);

  const colorGradient = useMemo(() => {
    return [
      new THREE.Color('#101835'), // low
      new THREE.Color('#7928ca'), // mid-low
      new THREE.Color('#00f0ff'), // mid
      new THREE.Color('#ff0080'), // high
      new THREE.Color('#00ff88'), // peak
    ];
  }, []);

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.getElapsedTime();

    let idx = 0;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        // Amplitude from real normalized log-mel data or procedural oscillation
        let amp = 0.2;
        if (data && data[r] && data[r][c] !== undefined) {
          // Normalize [-2, 2] to [0.1, 1.8]
          const val = data[r][c];
          amp = THREE.MathUtils.clamp((val + 1.5) / 2.5, 0.1, 2.2);
        } else {
          amp = (Math.sin(c * 0.4 + time * 2) * Math.cos(r * 0.3 + time * 1.5) + 1.2) * 0.6;
        }

        const posX = (c - cols / 2) * 0.12;
        const posZ = (r - rows / 2) * 0.12;
        const posY = amp / 2;

        dummy.position.set(posX, posY, posZ);
        dummy.scale.set(0.085, amp, 0.085);
        dummy.updateMatrix();
        meshRef.current.setMatrixAt(idx, dummy.matrix);

        // Color based on height/amplitude
        const norm = THREE.MathUtils.clamp(amp / 2.0, 0, 1);
        let colorIndex = norm * (colorGradient.length - 1);
        let baseIndex = Math.floor(colorIndex);
        let nextIndex = Math.min(baseIndex + 1, colorGradient.length - 1);
        let factor = colorIndex - baseIndex;

        const col = colorGradient[baseIndex].clone().lerp(colorGradient[nextIndex], factor);
        meshRef.current.setColorAt(idx, col);

        idx++;
      }
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  });

  return (
    <group position={[0, -0.6, 0]}>
      <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          roughness={0.2}
          metalness={0.8}
          emissive="#120c2b"
          emissiveIntensity={0.2}
        />
      </instancedMesh>
      <gridHelper args={[cols * 0.13, cols, '#ff0080', '#1c2438']} position={[0, 0, 0]} />
    </group>
  );
}

export default function SpectrogramVisualizer3D({
  spectrogramData,
  audioDuration = 2.0
}: {
  spectrogramData?: number[][];
  audioDuration?: number;
}) {
  const [hasWebGL, setHasWebGL] = useState(true);

  useEffect(() => {
    setHasWebGL(isWebGLAvailable());
  }, []);

  if (!hasWebGL) {
    return (
      <div className="spec-3d-fallback">
        <span className="cyber-mono">3D SPECTROGRAM RENDERER · WEBGL DISABLED</span>
      </div>
    );
  }

  return (
    <div className="spectrogram-3d-wrapper">
      <div className="spec-3d-header">
        <div>
          <span className="badge-chip text-cyan">3D ACOUSTIC TOPOGRAPHY</span>
          <span className="cyber-mono text-muted ml-2">64 MEL BANDS · {audioDuration}s WINDOW</span>
        </div>
        <span className="text-muted cyber-mono text-xs">ROTATE TO INSPECT FREQUENCY DENSITY</span>
      </div>

      <Canvas
        camera={{ position: [2.5, 2.2, 3.2], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width: '100%', height: '240px', background: 'transparent' }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={1.2} />
        <pointLight position={[-4, 4, -4]} color="#ff0080" intensity={0.9} />
        <pointLight position={[4, 2, 4]} color="#00f0ff" intensity={0.9} />

        <SpectrogramGrid3D data={spectrogramData} />

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          maxPolarAngle={Math.PI / 2.1}
          minPolarAngle={Math.PI / 6}
          autoRotate={true}
          autoRotateSpeed={0.8}
        />
      </Canvas>
    </div>
  );
}
