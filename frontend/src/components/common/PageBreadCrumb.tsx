interface BreadcrumbProps {
  pageTitle: string;
}

/** Title of a screen. The location itself is shown by the breadcrumb of the top bar. */
const PageBreadcrumb: React.FC<BreadcrumbProps> = ({ pageTitle }) => {
  return (
    <div className="mb-6">
      <h1 className="page-title">{pageTitle}</h1>
    </div>
  );
};

export default PageBreadcrumb;
