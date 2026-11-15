import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';
import { isWebGLAvailable } from '../../utils/webgl';

function NeuralSynapseNetwork({ isScanning }: { isScanning: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const nodes = useMemo(() => {
    const list: THREE.Vector3[] = [];
    const count = 28;
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const r = 1.3 + Math.random() * 0.7;
      list.push(new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      ));
    }
    return list;
  }, []);

  const lines = useMemo(() => {
    const segments: THREE.Vector3[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i].distanceTo(nodes[j]) < 1.1) {
          segments.push(nodes[i], nodes[j]);
        }
      }
    }
    return new THREE.BufferGeometry().setFromPoints(segments);
  }, [nodes]);

  useFrame((_, delta) => {
    if (groupRef.current) {
      const speed = isScanning ? 0.35 : 0.08;
      groupRef.current.rotation.y += delta * speed;
      groupRef.current.rotation.x += delta * (speed * 0.4);
    }
  });

  return (
    <group ref={groupRef}>
      {/* Neural Synapse Lines */}
      <primitive object={new THREE.LineSegments(lines, new THREE.LineBasicMaterial({
        color: isScanning ? '#ff0080' : '#7928ca',
        transparent: true,
        opacity: isScanning ? 0.55 : 0.3,
        blending: THREE.AdditiveBlending
      }))} />

      {/* Neural Node Spheres */}
      {nodes.map((pos, idx) => (
        <mesh key={idx} position={pos}>
          <sphereGeometry args={[0.038, 12, 12]} />
          <meshBasicMaterial
            color={idx % 3 === 0 ? '#00f0ff' : idx % 3 === 1 ? '#ff0080' : '#10b981'}
          />
        </mesh>
      ))}
    </group>
  );
}

function ScanningLaserDeck({ isScanning }: { isScanning: boolean }) {
  const laserRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (laserRef.current) {
      // Traverse scan plane up and down
      const range = 1.6;
      const speed = isScanning ? 3.5 : 1.2;
      laserRef.current.position.y = Math.sin(t * speed) * range;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = t * (isScanning ? 1.5 : 0.4);
    }
  });

  return (
    <group>
      {/* Base Grid Platter */}
      <gridHelper args={[3.8, 18, '#ff0080', '#1a2238']} position={[0, -1.8, 0]} />

      {/* Holographic Concentric Scanner Rings */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.75, 0]}>
        <ringGeometry args={[0.9, 1.8, 48]} />
        <meshBasicMaterial
          color="#00f0ff"
          transparent
          opacity={isScanning ? 0.4 : 0.18}
          wireframe
        />
      </mesh>

      {/* Dynamic Laser Scanning Plane */}
      <mesh ref={laserRef} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[3.4, 3.4]} />
        <meshBasicMaterial
          color={isScanning ? '#00ff88' : '#00f0ff'}
          transparent
          opacity={isScanning ? 0.28 : 0.12}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}

export default function CyberScanner3D({
  isScanning = false,
  modality = 'audio'
}: {
  isScanning?: boolean;
  modality?: 'image' | 'video' | 'audio' | 'fusion';
}) {
  const [hasWebGL, setHasWebGL] = useState(true);

  useEffect(() => {
    setHasWebGL(isWebGLAvailable());
  }, []);

  if (!hasWebGL) {
    return (
      <div className="cyber-scanner-fallback">
        <div className={`scan-line ${isScanning ? 'scanning' : ''}`} />
        <div className="fallback-text">
          <span>FORENSIC SCANNER ACTIVE · {modality.toUpperCase()}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="cyber-scanner-container">
      <div className="scanner-overlay-status">
        <span className={`scanner-indicator ${isScanning ? 'pulse-lime' : 'pulse-cyan'}`}>
          {isScanning ? 'ACTIVE FORENSIC INGESTION' : 'STANDBY · READY FOR BITSTREAM'}
        </span>
        <span className="cyber-mono text-muted">TARGET: {modality.toUpperCase()} MODALITY</span>
      </div>

      <Canvas
        camera={{ position: [0, 1.2, 4.2], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width: '100%', height: '100%', background: 'transparent' }}
      >
        <ambientLight intensity={0.5} />
        <pointLight position={[3, 3, 3]} color="#00f0ff" intensity={1} />
        <pointLight position={[-3, -3, -3]} color="#ff0080" intensity={0.8} />

        <Float speed={1.5} rotationIntensity={0.2} floatIntensity={0.2}>
          <NeuralSynapseNetwork isScanning={isScanning} />
          <ScanningLaserDeck isScanning={isScanning} />
        </Float>
      </Canvas>
    </div>
  );
}
