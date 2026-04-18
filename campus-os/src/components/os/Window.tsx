import { MouseEvent as ReactMouseEvent, useRef } from 'react';
import { WindowState, useOsStore } from '../../store/osStore';
import TrafficLights from './TrafficLights';

interface WindowProps {
  windowData: WindowState;
  children: React.ReactNode;
}

export default function Window({ windowData, children }: WindowProps) {
  const focusWindow = useOsStore((state) => state.focusWindow);
  const closeWindow = useOsStore((state) => state.closeWindow);
  const moveWindow = useOsStore((state) => state.moveWindow);
  const dragOffset = useRef({ x: 0, y: 0 });

  const startDrag = (event: ReactMouseEvent<HTMLElement>) => {
    event.preventDefault();
    focusWindow(windowData.id);
    dragOffset.current = {
      x: event.clientX - windowData.x,
      y: event.clientY - windowData.y,
    };

    const onMove = (moveEvent: MouseEvent) => {
      const nextX = Math.max(0, moveEvent.clientX - dragOffset.current.x);
      const nextY = Math.max(36, moveEvent.clientY - dragOffset.current.y);
      moveWindow(windowData.id, nextX, nextY);
    };

    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  return (
    <article
      className="window glass-panel"
      onMouseDown={() => focusWindow(windowData.id)}
      style={{
        width: windowData.width,
        height: windowData.height,
        transform: `translate(${windowData.x}px, ${windowData.y}px)`,
        zIndex: windowData.zIndex,
      }}
    >
      <div className="window-header" onMouseDown={startDrag}>
        <TrafficLights onClose={() => closeWindow(windowData.id)} />
        <div className="window-toolbar-pill" />
        <span className="window-title">{windowData.title}</span>
      </div>
      <div className="window-body">{children}</div>
    </article>
  );
}
