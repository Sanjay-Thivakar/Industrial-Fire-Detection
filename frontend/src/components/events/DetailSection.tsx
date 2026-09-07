import React from 'react';

export interface DetailSectionProps {
  title: string;
  badge?: React.ReactNode;
  icon?: string;
  children: React.ReactNode;
  disclaimer?: string;
}

export const DetailSection: React.FC<DetailSectionProps> = ({
  title,
  badge,
  icon,
  children,
  disclaimer,
}) => {
  return (
    <div className="drawer-section">
      <div className="drawer-section-header">
        <div className="section-title-wrapper">
          {icon && <span className="section-icon">{icon}</span>}
          <h4 className="section-heading">{title}</h4>
        </div>
        {badge && <div className="section-badge-wrapper">{badge}</div>}
      </div>

      <div className="drawer-section-body">{children}</div>

      {disclaimer && <div className="drawer-section-disclaimer">{disclaimer}</div>}
    </div>
  );
};
