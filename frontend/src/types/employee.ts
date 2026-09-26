export interface FamilyMember {
  id?: number;
  name: string;
  date_of_birth: string;
  relationship: 'SPOUSE' | 'CHILD' | 'OTHER';
}

export interface EmployeeDocument {
  id?: number;
  document_type: 'ID' | 'DIPLOMA' | 'CONTRACT' | 'MEDICAL' | 'DISCIPLINARY' | 'OTHER';
  name: string;
  file?: File | string;
  validity_date?: string | null;
}

export interface EducationAndExperience {
  id?: number;
  entry_type: 'EDUCATION' | 'EXPERIENCE' | 'LANGUAGE';
  title: string;
  institution_or_company: string;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
}

export interface EmployeeHistory {
  id: number;
  author: number;
  modification_date: string;
  field_name: string;
  previous_value: string | null;
  new_value: string | null;
}

export interface Employee {
  id?: number;
  user?: number | null;
  matriculation_number?: string;
  status: 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';
  
  // Civil Identity
  surname: string;
  given_names: string;
  date_of_birth: string;
  place_of_birth: string;
  sex: 'M' | 'F';
  nationality: string;
  marital_status: 'SINGLE' | 'MARRIED' | 'DIVORCED' | 'WIDOWED';
  identity_document_type: string;
  identity_document_number: string;
  identity_document_validity?: string | null;
  photograph?: File | string | null;

  // Contact Details
  address: string;
  phone_number: string;
  personal_email?: string | null;
  professional_email?: string | null;
  emergency_contact_name: string;
  emergency_contact_number: string;

  // Social & Tax
  social_insurance_number?: string | null;
  tax_identification_number?: string | null;
  professional_identification?: string | null;

  // Bank Details
  bank_name?: string | null;
  bank_branch?: string | null;
  account_number?: string | null;
  bank_key?: string | null;
  method_of_payment: 'TRANSFER' | 'CHEQUE' | 'CASH';

  // Administrative
  department?: number | null;
  position?: number | null;
  classification?: number | null;
  contract_type: 'PERMANENT' | 'FIXED_TERM' | 'INTERNSHIP' | 'TEMPORARY' | 'APPRENTICESHIP' | 'SERVICE';
  date_of_hire: string;
  workplace?: number | null;

  // Nested
  family_members?: FamilyMember[];
  documents?: EmployeeDocument[];
  education_experience?: EducationAndExperience[];
  history?: EmployeeHistory[];
}
