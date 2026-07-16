/**
 * Professional medical illustration: pregnant researcher in laboratory.
 *
 * Style: Clean healthcare infographic — warm, inclusive, professional.
 * Inspired by medical textbook and healthcare app illustrations.
 * Deliberately avoids AI/cartoon aesthetic.
 */
export default function PregnancyIllustration({
  className = "",
  size = 380,
}: {
  className?: string;
  size?: number;
}) {
  const s = size;
  // Scale everything proportionally
  const scale = s / 400;

  return (
    <svg
      width={s}
      height={s}
      viewBox="0 0 400 400"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Pregnant researcher working safely in a laboratory"
      role="img"
    >
      {/* ── Background: soft cream circle ── */}
      <circle cx="200" cy="200" r="190" fill="#FFF9F5" />
      <circle cx="200" cy="200" r="188" stroke="#FCE4EC" strokeWidth="1.5" strokeDasharray="6 4" />

      {/* ── Lab bench (wooden/warm tone) ── */}
      <rect x="50" y="290" width="300" height="14" rx="4" fill="#E8D5C4" stroke="#D4BFAF" strokeWidth="1.5" />
      <rect x="70" y="304" width="8" height="44" rx="2" fill="#C4A891" />
      <rect x="322" y="304" width="8" height="44" rx="2" fill="#C4A891" />

      {/* ── Microscope (clean, minimal) ── */}
      <rect x="290" y="230" width="7" height="60" rx="2" fill="#8BB8D9" />
      <rect x="278" y="225" width="31" height="10" rx="3" fill="#7AAAD3" />
      <circle cx="293" cy="218" r="6" fill="#A2C6E3" stroke="#8BB8D9" strokeWidth="1" />
      <rect x="275" y="260" width="14" height="30" rx="3" fill="#8D8678" />

      {/* ── Chemical bottle ── */}
      <rect x="105" y="252" width="24" height="38" rx="3" fill="#A8D5BA" opacity="0.5" stroke="#7DBA98" strokeWidth="1.5" />
      <rect x="112" y="244" width="10" height="10" rx="2" fill="#A8D5BA" opacity="0.3" stroke="#7DBA98" strokeWidth="1" />

      {/* ── Flask ── */}
      <path d="M72 260 L78 260 L82 298 L68 298 Z" fill="#8BB8D9" opacity="0.4" stroke="#7AAAD3" strokeWidth="1.5" />
      <rect x="73" y="252" width="4" height="10" rx="1" fill="#7AAAD3" opacity="0.5" />

      {/* ── Researcher ── */}

      {/* Lab coat body */}
      <path
        d="M168 188 L168 298 Q168 306 160 306 L240 306 Q232 306 232 298 L232 188"
        fill="white"
        stroke="#D4BFAF"
        strokeWidth="2"
      />
      {/* Lab coat collar / lapels */}
      <path d="M200 188 L185 248" stroke="#E0D0C0" strokeWidth="2" />
      <path d="M200 188 L215 248" stroke="#E0D0C0" strokeWidth="2" />
      {/* Pocket */}
      <rect x="180" y="260" width="16" height="14" rx="2" fill="none" stroke="#E0D0C0" strokeWidth="1.5" />
      <rect x="204" y="260" width="16" height="14" rx="2" fill="none" stroke="#E0D0C0" strokeWidth="1.5" />

      {/* Pregnant belly — soft, natural curve */}
      <ellipse cx="200" cy="252" rx="30" ry="32" fill="#FDE8EF" stroke="#F0C0D0" strokeWidth="2" />

      {/* Protective hand resting on belly */}
      <path
        d="M182 248 Q176 240 180 234 Q184 228 190 232"
        fill="#FCE4EC"
        stroke="#E8C8D4"
        strokeWidth="2"
        strokeLinecap="round"
      />

      {/* Head */}
      <circle cx="200" cy="152" r="26" fill="#FCE4EC" stroke="#F0C0D0" strokeWidth="1.5" />

      {/* Hair — simple, professional */}
      <path d="M174 150 Q174 124 200 122 Q226 124 226 150" fill="#6B5B4F" />
      <path d="M174 150 Q176 126 200 122 Q224 126 226 150 Q218 138 200 136 Q182 138 174 150Z" fill="#5A4A3F" />

      {/* Face — calm, professional expression */}
      <circle cx="190" cy="152" r="2.5" fill="#3D3833" />
      <circle cx="210" cy="152" r="2.5" fill="#3D3833" />
      <path d="M194 160 Q200 166 206 160" stroke="#8D8678" strokeWidth="1.5" strokeLinecap="round" fill="none" />

      {/* Safety glasses */}
      <rect x="181" y="145" width="18" height="11" rx="4" fill="white" fillOpacity="0.5" stroke="#8BB8D9" strokeWidth="1.5" />
      <rect x="201" y="145" width="18" height="11" rx="4" fill="white" fillOpacity="0.5" stroke="#8BB8D9" strokeWidth="1.5" />
      <line x1="199" y1="150" x2="201" y2="150" stroke="#8BB8D9" strokeWidth="1.5" />

      {/* Left arm — holding clip board */}
      <path d="M168 195 Q148 215 142 248" stroke="#FCE4EC" strokeWidth="9" strokeLinecap="round" fill="none" />
      <rect x="120" y="238" width="34" height="46" rx="3" fill="#FFF9F5" stroke="#E0D0C0" strokeWidth="1.5" />
      <rect x="126" y="246" width="22" height="3" rx="1" fill="#C4A891" />
      <rect x="126" y="253" width="22" height="3" rx="1" fill="#C4A891" />
      <rect x="126" y="260" width="16" height="3" rx="1" fill="#C4A891" />

      {/* Right arm — relaxed at side */}
      <path d="M232 195 Q250 212 248 240" stroke="#FCE4EC" strokeWidth="9" strokeLinecap="round" fill="none" />

      {/* ── Safety indicators (subtle) ── */}
      {/* Shield badge upper left: EHS certified feel */}
      <circle cx="54" cy="56" r="14" fill="#A8D5BA" opacity="0.3" />
      <path d="M48 56 L52 61 L62 51" stroke="#5CA07B" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />

      {/* Small cross (medical) upper right */}
      <circle cx="348" cy="56" r="14" fill="#8BB8D9" opacity="0.3" />
      <path d="M344 56 L352 56 M348 52 L348 60" stroke="#4D91BF" strokeWidth="2" strokeLinecap="round" />

      {/* ── Decorative elements ── */}
      {/* Small molecules / safe structure */}
      <circle cx="320" cy="130" r="8" fill="none" stroke="#E0D0C0" strokeWidth="1" opacity="0.5" />
      <circle cx="340" cy="120" r="5" fill="none" stroke="#E0D0C0" strokeWidth="1" opacity="0.5" />
      <path d="M326 126 L336 122" stroke="#E0D0C0" strokeWidth="0.8" opacity="0.5" />
    </svg>
  );
}

/** Small icon for navbar */
export function PregnancyIcon({ className = "", size = 48 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className} aria-hidden="true">
      <circle cx="24" cy="24" r="23" fill="#FFF9F5" stroke="#FCE4EC" strokeWidth="1.5" />
      <circle cx="24" cy="19" r="5.5" fill="#FCE4EC" />
      <ellipse cx="24" cy="33" rx="9" ry="9" fill="#FDE8EF" stroke="#F0C0D0" strokeWidth="1.5" />
      <path d="M17 28 Q21 25 24 27 Q27 25 31 28" stroke="#E88BA7" strokeWidth="1.2" strokeLinecap="round" fill="none" opacity="0.6" />
    </svg>
  );
}
