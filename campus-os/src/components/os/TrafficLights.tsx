interface TrafficLightsProps {
  onClose: () => void;
  onMaximize?: () => void;
}

export default function TrafficLights({ onClose, onMaximize }: TrafficLightsProps) {
  return (
    <div className="traffic-lights">
      <button type="button" aria-label="Close window" className="tl tl-red" onClick={onClose} />
      <button type="button" aria-label="Minimize window" className="tl tl-yellow" />
      <button type="button" aria-label="Maximize window" className="tl tl-green" onClick={onMaximize} />
    </div>
  );
}
