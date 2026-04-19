import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import Desk from './Desk';
import MacBook from './MacBook';

type CameraRigProps = {
  zooming: boolean;
  onZoomComplete: () => void;
};

function CameraRig({ zooming, onZoomComplete }: CameraRigProps) {
  const { camera } = useThree();
  const from = useRef(new THREE.Vector3(4, 2.8, 5.6));
  const to = useRef(new THREE.Vector3(0.75, 1.28, 2.05));
  const progress = useRef(0);
  const started = useRef(false);
  const completed = useRef(false);

  useEffect(() => {
    if (zooming) {
      started.current = true;
      progress.current = 0;
      completed.current = false;
    }
  }, [zooming]);

  useFrame((_, delta) => {
    if (!started.current || completed.current) return;

    progress.current = Math.min(1, progress.current + delta * 0.62);
    const t = 1 - (1 - progress.current) ** 3;
    camera.position.lerpVectors(from.current, to.current, t);
    camera.lookAt(0, 0.32, 0);

    if (progress.current >= 1 && !completed.current) {
      completed.current = true;
      onZoomComplete();
    }
  });

  return null;
}

type LandingSceneProps = {
  zooming: boolean;
  onZoomComplete: () => void;
  onMacBookClick: () => void;
};

export default function LandingScene({
  zooming,
  onZoomComplete,
  onMacBookClick,
}: LandingSceneProps) {
  return (
    <>
      <color attach="background" args={['#1e2229']} />
      <fog attach="fog" args={['#1e2229', 14, 32]} />
      <ambientLight intensity={0.5} />
      <directionalLight
        position={[6, 10, 5]}
        intensity={1.15}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-far={20}
        shadow-camera-left={-8}
        shadow-camera-right={8}
        shadow-camera-top={8}
        shadow-camera-bottom={-8}
      />
      <spotLight position={[-3, 7, 3]} intensity={0.4} angle={0.55} penumbra={0.85} />
      <Desk />
      <MacBook onOpen={onMacBookClick} />
      <CameraRig zooming={zooming} onZoomComplete={onZoomComplete} />
    </>
  );
}
