import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Float } from '@react-three/drei';
import * as THREE from 'three';
import { isWebGLAvailable } from '../../utils/webgl';

// Convert Lat/Lng to 3D Sphere coordinates
function latLngToVector3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const z = radius * Math.sin(phi) * Math.sin(theta);
  const y = radius * Math.cos(phi);
  return new THREE.Vector3(x, y, z);
}

// Major cyber media threat sensor telemetry points
const THREAT_NODES = [
  { name: 'US-EAST / Deepfake Node A7', lat: 38.9, lon: -77.0, risk: 'high', type: 'Voice Clone Clustered' },
  { name: 'EU-CENTRAL / Forensic Core 02', lat: 50.1, lon: 8.6, risk: 'medium', type: 'Diffusion Face Swap' },
  { name: 'AP-NORTHEAST / Telemetry Node T9', lat: 35.6, lon: 139.6, risk: 'high', type: 'Biometric Spoof Surge' },
  { name: 'UK-SOUTH / Media Guard London', lat: 51.5, lon: -0.12, risk: 'medium', type: 'Temporal Inconsistency' },
  { name: 'AP-SOUTHEAST / Sentinel SG', lat: 1.35, lon: 103.8, risk: 'low', type: 'Acoustic Synthesis' },
  { name: 'IN-WEST / Cyber Guard Mumbai', lat: 19.0, lon: 72.8, risk: 'medium', type: 'Speech Lip-Sync' },
  { name: 'SA-EAST / Telemetry Brazil', lat: -23.5, lon: -46.6, risk: 'high', type: 'Adversarial Injection' },
  { name: 'AU-EAST / Forensic Lab Sydney', lat: -33.8, lon: 151.2, risk: 'low', type: 'Spec-Frequency Drift' },
];

// Arcs connecting threat nodes
const THREAT_ARCS = [
  [0, 1], // US to EU
  [1, 3], // EU to UK
  [0, 6], // US to Brazil
  [1, 5], // EU to India
  [5, 4], // India to SG
  [4, 2], // SG to Tokyo
  [2, 7], // Tokyo to Sydney
];

function ThreatArc({ start, end, color }: { start: THREE.Vector3; end: THREE.Vector3; color: string }) {
  const curve = useMemo(() => {
    // Elevate the midpoint for high arc trajectory
    const mid = start.clone().lerp(end, 0.5);
    const distance = start.distanceTo(end);
    mid.normalize().multiplyScalar(2.0 + distance * 0.25);
    return new THREE.QuadraticBezierCurve3(start, mid, end);
  }, [start, end]);

  const points = useMemo(() => curve.getPoints(50), [curve]);
  const lineGeometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

  return (
    <primitive object={new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({
      color: new THREE.Color(color),
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
      linewidth: 1
    }))} />
  );
}

function HolographicSphere() {
  const sphereRef = useRef<THREE.Group>(null);
  const ringRef1 = useRef<THREE.Mesh>(null);
  const ringRef2 = useRef<THREE.Mesh>(null);
  const dotsRef = useRef<THREE.Points>(null);

  // Generate glowing grid surface points
  const globePoints = useMemo(() => {
    const coords: number[] = [];
    const radius = 2.0;
    const count = 1800;
    for (let i = 0; i < count; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = radius * (1.0 + (Math.random() - 0.5) * 0.02);
      coords.push(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      );
    }
    return new Float32Array(coords);
  }, []);

  useFrame((_, delta) => {
    if (sphereRef.current) {
      sphereRef.current.rotation.y += delta * 0.08;
    }
    if (ringRef1.current) {
      ringRef1.current.rotation.z += delta * 0.12;
      ringRef1.current.rotation.x += delta * 0.05;
    }
    if (ringRef2.current) {
      ringRef2.current.rotation.y -= delta * 0.15;
    }
  });

  const nodeVectors = useMemo(() => {
    return THREAT_NODES.map(node => latLngToVector3(node.lat, node.lon, 2.0));
  }, []);

  return (
    <group ref={sphereRef}>
      {/* Semi-transparent wireframe core */}
      <mesh>
        <sphereGeometry args={[1.98, 36, 36]} />
        <meshBasicMaterial
          color="#161233"
          wireframe
          transparent
          opacity={0.18}
        />
      </mesh>

      {/* Cyber point cloud representing planet contours */}
      <points ref={dotsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[globePoints, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.032}
          color="#00f0ff"
          transparent
          opacity={0.65}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Outer orbital equator rings */}
      <mesh ref={ringRef1} rotation={[Math.PI / 4, 0, 0]}>
        <ringGeometry args={[2.35, 2.37, 64]} />
        <meshBasicMaterial
          color="#ff0080"
          transparent
          opacity={0.4}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh ref={ringRef2} rotation={[-Math.PI / 3, Math.PI / 6, 0]}>
        <ringGeometry args={[2.55, 2.57, 64]} />
        <meshBasicMaterial
          color="#7928ca"
          transparent
          opacity={0.35}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Cyber threat arcs */}
      {THREAT_ARCS.map(([startIdx, endIdx], i) => (
        <ThreatArc
          key={i}
          start={nodeVectors[startIdx]}
          end={nodeVectors[endIdx]}
          color={i % 2 === 0 ? '#ff0080' : '#00f0ff'}
        />
      ))}

      {/* Pulsing sensor node beacons */}
      {THREAT_NODES.map((node, i) => {
        const pos = nodeVectors[i];
        const color = node.risk === 'high' ? '#ff0080' : node.risk === 'medium' ? '#f59e0b' : '#00f0ff';
        return (
          <group key={i} position={pos}>
            <mesh>
              <sphereGeometry args={[0.045, 16, 16]} />
              <meshBasicMaterial color={color} />
            </mesh>
            <mesh>
              <ringGeometry args={[0.07, 0.085, 24]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={0.7}
                side={THREE.DoubleSide}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function HoloGlobeFallback() {
  return (
    <div className="holo-globe-fallback">
      <div className="radar-screen">
        <div className="radar-sweep" />
        <div className="radar-ring ring-1" />
        <div className="radar-ring ring-2" />
        <div className="radar-ring ring-3" />
        {THREAT_NODES.map((node, i) => (
          <div
            key={i}
            className={`radar-blip blip-${node.risk}`}
            style={{
              top: `${50 - node.lat * 0.4}%`,
              left: `${50 + node.lon * 0.22}%`
            }}
            title={`${node.name}: ${node.type}`}
          />
        ))}
      </div>
      <div className="fallback-caption">
        <span>GLOBAL THREAT MATRIX · 2D RADAR FALLBACK</span>
      </div>
    </div>
  );
}

export default function HoloGlobe({ activeThreatCount = 8 }: { activeThreatCount?: number }) {
  const [hasWebGL, setHasWebGL] = useState(true);

  useEffect(() => {
    setHasWebGL(isWebGLAvailable());
  }, []);

  if (!hasWebGL) {
    return <HoloGlobeFallback />;
  }

  return (
    <div className="holo-globe-container">
      <div className="globe-overlay-hud">
        <div className="hud-badge">
          <span className="beacon-dot pulse-cyan" />
          <span>CYBER SURVEILLANCE FEED</span>
        </div>
        <div className="hud-stats">
          <div><small>ACTIVE SENSORS</small><strong>{activeThreatCount} NODES</strong></div>
          <div><small>GLOBAL STATUS</small><strong className="text-cyan">MONITORING</strong></div>
        </div>
      </div>

      <Canvas
        camera={{ position: [0, 0, 5.2], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'default' }}
        style={{ width: '100%', height: '100%', background: 'transparent' }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <pointLight position={[-5, -5, -5]} color="#7928ca" intensity={0.6} />

        <Float speed={1.2} rotationIntensity={0.2} floatIntensity={0.3}>
          <HolographicSphere />
        </Float>

        <Stars radius={40} depth={30} count={600} factor={3} saturation={0} fade speed={1} />
        <OrbitControls
          enablePan={false}
          enableZoom={true}
          minDistance={3.8}
          maxDistance={7.5}
          autoRotate={true}
          autoRotateSpeed={0.6}
          dampingFactor={0.05}
        />
      </Canvas>

      <div className="globe-footer-hud">
        <span className="cyber-mono">LAT/LONG GRID · 3D ORBIT ACTIVE · DRAG TO ROTATE</span>
      </div>
    </div>
  );
}
