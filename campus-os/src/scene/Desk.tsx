export default function Desk() {
  return (
    <group position={[0, 0, 0]}>
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[24, 24]} />
        <meshStandardMaterial color="#3a3228" roughness={0.88} metalness={0.05} />
      </mesh>
    </group>
  );
}
