import { ThreeEvent } from '@react-three/fiber';
import { RoundedBox } from '@react-three/drei';

type MacBookProps = {
  onOpen: () => void;
};

/**
 * Modèle procédural (style MacBook fermé + couvercle).
 * Remplacez par un GLB sous /models/macbook.glb si vous ajoutez un fichier.
 */
export default function MacBook({ onOpen }: MacBookProps) {
  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onOpen();
  };

  const handlePointerOver = () => {
    document.body.style.cursor = 'pointer';
  };

  const handlePointerOut = () => {
    document.body.style.cursor = 'auto';
  };

  return (
    <group position={[0, 0.06, 0.2]}>
      <group
        onClick={handleClick}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
      >
        <RoundedBox
          args={[2.4, 0.11, 1.65]}
          radius={0.035}
          smoothness={4}
          castShadow
          receiveShadow
          position={[0, 0.055, 0]}
        >
          <meshStandardMaterial color="#b8b8bd" metalness={0.45} roughness={0.42} />
        </RoundedBox>
        <RoundedBox
          args={[2.38, 0.025, 1.62]}
          radius={0.02}
          smoothness={3}
          castShadow
          position={[0, 0.125, -0.12]}
          rotation={[-0.32, 0, 0]}
        >
          <meshStandardMaterial color="#0d0d0f" metalness={0.25} roughness={0.35} />
        </RoundedBox>
      </group>
    </group>
  );
}
