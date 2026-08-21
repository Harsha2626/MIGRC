def build_badge_svg(label, value, color=None):
    """Shields.io-style flat badge SVG. Color auto-derives from a trailing '%' in value if not given."""
    if color is None:
        pct = None
        try:
            pct = int(str(value).rstrip('%'))
        except ValueError:
            pct = None
        if pct is None:
            color = '#3b82f6'
        elif pct >= 90:
            color = '#10b981'
        elif pct >= 70:
            color = '#f59e0b'
        else:
            color = '#ef4444'

    label_w = 6 * len(label) + 20
    value_w = 6 * len(value) + 20
    total_w = label_w + value_w

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
    <rect width="{total_w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_w / 2}" y="14">{label}</text>
    <text x="{label_w + value_w / 2}" y="14">{value}</text>
  </g>
</svg>'''
