const fs = require('fs');
const r = (f, pat, rep) => {
  if (fs.existsSync(f)) {
    fs.writeFileSync(f, fs.readFileSync(f, 'utf8').replace(pat, rep));
  }
};
const files = [
  'src/pages/Employees/EmployeeProfile.tsx',
  'src/pages/Organisation/components/ClassificationsTable.tsx',
  'src/pages/Organisation/components/CostCentresTable.tsx',
  'src/pages/Organisation/components/DepartmentsTable.tsx',
  'src/pages/Organisation/components/PositionsTable.tsx',
  'src/pages/Organisation/components/SitesTable.tsx',
  'src/pages/Organisation/OrganisationSettings.tsx'
];
files.forEach(f => r(f, /import React(?:, \{[^}]+\})? from ['"]react['"];?\n?/, (m) => m.includes('{') ? m.replace(/React, /, '') : ''));

r('src/context/ToastContext.tsx', /import \{ createContext, useContext, useState, ReactNode \} from 'react';/, "import { createContext, useContext, useState } from 'react';\nimport type { ReactNode } from 'react';");
r('src/pages/Employees/EmployeeForm.tsx', /isValidPhoneNumber, /, '');
r('src/pages/Employees/EmployeeForm.tsx', /const \{ state \} = useLocation\(\);/, 'useLocation();');
r('src/pages/Employees/EmployeeForm.tsx', /catch \(err\)/g, 'catch (_err)');
r('src/pages/Organisation/components/ClassificationModal.tsx', /value=\{formData\.level\}/, "value={formData.level.toString()}");
r('src/pages/Organisation/components/DepartmentModal.tsx', /onChange=\{\(e\) => setFormData\(\{ \.\.\.formData, cost_centre: e \}\)\}/, "onChange={(e: any) => setFormData({ ...formData, cost_centre: typeof e === 'string' ? e : e.target.value })}");
r('src/pages/Organisation/components/DepartmentModal.tsx', /onChange=\{\(value\) => setFormData\(\{ \.\.\.formData, cost_centre: value \}\)\}/, "onChange={(value: string | any) => setFormData({ ...formData, cost_centre: typeof value === 'string' ? value : value.target?.value })}");
