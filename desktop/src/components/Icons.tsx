// Iconos de trazo (24×24), decorativos: aria-hidden. El texto acompaña siempre al icono.

import type { ReactNode } from "react";

function Svg({ size = 20, children, stroke = 2 }: { size?: number; children: ReactNode; stroke?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

type P = { size?: number };

export const IconRadar = ({ size }: P) => (
  <Svg size={size}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="4" />
    <path d="M12 12 18 6" />
  </Svg>
);
export const IconHome = ({ size }: P) => (
  <Svg size={size}>
    <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" />
  </Svg>
);
export const IconTarget = ({ size }: P) => (
  <Svg size={size}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <circle cx="12" cy="12" r="1" />
  </Svg>
);
export const IconFlag = ({ size }: P) => (
  <Svg size={size}>
    <path d="M5 21V4h11l-2 4 2 4H5" />
  </Svg>
);
export const IconWallet = ({ size }: P) => (
  <Svg size={size}>
    <rect x="3" y="6" width="18" height="14" rx="2" />
    <path d="M3 10h18M16 15h2" />
  </Svg>
);
export const IconBook = ({ size }: P) => (
  <Svg size={size}>
    <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" />
    <path d="M4 19V5" />
  </Svg>
);
export const IconCap = ({ size }: P) => (
  <Svg size={size}>
    <path d="m2 9 10-5 10 5-10 5z" />
    <path d="M6 11v5c3 2 9 2 12 0v-5" />
  </Svg>
);
export const IconUser = ({ size }: P) => (
  <Svg size={size}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c1-4 4.5-6 8-6s7 2 8 6" />
  </Svg>
);
export const IconSliders = ({ size }: P) => (
  <Svg size={size}>
    <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12" />
    <circle cx="16" cy="6" r="2" />
    <circle cx="10" cy="12" r="2" />
    <circle cx="18" cy="18" r="2" />
  </Svg>
);
export const IconSearch = ({ size = 18 }: P) => (
  <Svg size={size}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </Svg>
);
export const IconMoon = ({ size = 18 }: P) => (
  <Svg size={size}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />
  </Svg>
);
export const IconSun = ({ size = 18 }: P) => (
  <Svg size={size}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Svg>
);
export const IconCheckCircle = ({ size = 16 }: P) => (
  <Svg size={size} stroke={2.3}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8 12 3 3 5-6" />
  </Svg>
);
export const IconEye = ({ size = 16 }: P) => (
  <Svg size={size} stroke={2.3}>
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
    <circle cx="12" cy="12" r="3" />
  </Svg>
);
export const IconBan = ({ size = 16 }: P) => (
  <Svg size={size} stroke={2.3}>
    <circle cx="12" cy="12" r="9" />
    <path d="m5.6 5.6 12.8 12.8" />
  </Svg>
);
export const IconShield = ({ size = 14 }: P) => (
  <Svg size={size}>
    <path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6z" />
  </Svg>
);
export const IconInfo = ({ size = 18 }: P) => (
  <Svg size={size}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8v.01" />
  </Svg>
);
export const IconArrowUp = ({ size = 18 }: P) => (
  <Svg size={size} stroke={2.2}>
    <path d="M12 19V5M5 12l7-7 7 7" />
  </Svg>
);
export const IconAlert = ({ size = 18 }: P) => (
  <Svg size={size} stroke={2.2}>
    <path d="M12 3 2 20h20z" />
    <path d="M12 10v4M12 17v.01" />
  </Svg>
);
export const IconBack = ({ size = 18 }: P) => (
  <Svg size={size}>
    <path d="M15 6l-6 6 6 6" />
  </Svg>
);
export const IconRefresh = ({ size = 16 }: P) => (
  <Svg size={size}>
    <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" />
  </Svg>
);
export const IconX = ({ size = 16 }: P) => (
  <Svg size={size} stroke={2.4}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Svg>
);
export const IconCheck = ({ size = 16 }: P) => (
  <Svg size={size} stroke={2.6}>
    <path d="m5 12 5 5 9-10" />
  </Svg>
);
