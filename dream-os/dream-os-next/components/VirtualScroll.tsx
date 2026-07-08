/**
 * VirtualScroll — 虚拟滚动消息列表
 * 使用 @tanstack/react-virtual，只渲染可视区域 ~15 条消息
 */
import React, { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

interface Props {
  items: Array<{ id: string; content: string }>;
  rowHeight?: number;
  maxHeight?: string;
}

export function VirtualScroll({ items, rowHeight = 40, maxHeight = '60vh' }: Props) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 5,
  });

  if (items.length === 0) return null;

  return (
    <div
      ref={parentRef}
      style={{
        maxHeight,
        overflowY: 'auto',
        width: '100%',
        contain: 'strict',
        padding: '8px 0',
      }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={items[virtualItem.index].id}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
              padding: '4px 0',
              fontSize: 14,
              lineHeight: 1.6,
              color: 'var(--textPrimary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {items[virtualItem.index].content}
          </div>
        ))}
      </div>
    </div>
  );
}
