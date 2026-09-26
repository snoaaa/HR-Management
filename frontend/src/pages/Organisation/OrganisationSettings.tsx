import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import PageMeta from "@/components/common/PageMeta";
import CompanyIdentityForm from "./components/CompanyIdentityForm";
import SitesTable from "./components/SitesTable";
import CostCentresTable from "./components/CostCentresTable";
import DepartmentsTable from "./components/DepartmentsTable";
import ClassificationsTable from "./components/ClassificationsTable";
import PositionsTable from "./components/PositionsTable";

export default function OrganisationSettings() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Read initial tab from URL hash, default to "identity"
  const getInitialTab = () => {
    const hash = location.hash.replace("#", "");
    return hash || "identity";
  };

  const [activeTab, setActiveTab] = useState<string>(getInitialTab());

  // Update hash when tab changes
  useEffect(() => {
    navigate(`#${activeTab}`, { replace: true });
  }, [activeTab, navigate]);

  // Sync state if user uses browser back/forward buttons
  useEffect(() => {
    const hash = location.hash.replace("#", "");
    if (hash && hash !== activeTab) {
      setActiveTab(hash);
    }
  }, [location.hash]);

  const tabs = [
    { id: "identity", label: "Company Identity" },
    { id: "sites", label: "Sites & Locations" },
    { id: "departments", label: "Departments (Org Chart)" },
    { id: "cost-centres", label: "Cost Centres" },
    { id: "positions", label: "Positions Catalogue" },
    { id: "classifications", label: "Classifications Grid" },
  ];

  return (
    <>
      <PageMeta
        title="Organisation Settings | HR Management System"
        description="Manage the core organisational structure, sites, departments, and positions."
      />
      <PageBreadcrumb pageTitle="Organisation Settings" />

      <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
        {/* Tabs Header */}
        <div className="flex overflow-x-auto border-b border-gray-200 hide-scrollbar dark:border-gray-800">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap border-b-2 px-6 py-4 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "border-brand-500 text-brand-500"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === "identity" && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
                  Company Identity
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Register the core identity of the organisation.
                </p>
              </div>
              <CompanyIdentityForm />
            </div>
          )}

          {activeTab === "sites" && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
                  Sites & Establishments
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage the physical locations of the company.
                </p>
              </div>
              <SitesTable />
            </div>
          )}

          {activeTab === "departments" && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
                  Organisational Hierarchy
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage divisions, departments, services, and teams.
                </p>
              </div>
              <DepartmentsTable />
            </div>
          )}

          {activeTab === "cost-centres" && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
                  Cost Centres
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage cost centres for accounting attachments.
                </p>
              </div>
              <CostCentresTable />
            </div>
          )}

          {activeTab === "positions" && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
                  Positions Catalogue
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage positions, required skills, and reporting lines.
                </p>
              </div>
              <PositionsTable />
            </div>
          )}

          {activeTab === "classifications" && (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
                  Classifications Grid
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage professional categories, grades, and coefficients.
                </p>
              </div>
              <ClassificationsTable />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
