export interface DemoEventDef {
  id: string;
  name: string;
  category: string;
  expectedClass: string;
  context: string;
}

export const DEMO_QUICK_PICK_EVENTS: readonly DemoEventDef[] = [
  {
    id: 'FIRMS_TN_0000',
    name: 'Salem Steel (SAIL)',
    category: 'Industrial',
    expectedClass: 'Industrial Thermal Activity',
    context: 'Substation & Metallurgy',
  },
  {
    id: 'FIRMS_TN_0008',
    name: 'JSW Steel (Mecheri)',
    category: 'Industrial',
    expectedClass: 'Industrial Thermal Activity',
    context: 'Steel Manufacturing Hotspot',
  },
  {
    id: 'FIRMS_TN_0001',
    name: 'Ramanathapuram',
    category: 'Agricultural',
    expectedClass: 'Agricultural Burning',
    context: 'Crop Residue Biomass',
  },
  {
    id: 'FIRMS_TN_0004',
    name: 'Quarry / Mining',
    category: 'Quarry',
    expectedClass: 'Agricultural Burning',
    context: 'High-FRP Extraction Site',
  },
];
