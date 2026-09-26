import api from './axiosConfig';
import { Employee, FamilyMember, EmployeeDocument, EducationAndExperience } from '../types/employee';

const EMPLOYEE_ENDPOINT = '/employees/';

export const employeeService = {
  // Core Employee
  getAll: async (params?: Record<string, any>) => {
    const response = await api.get<Employee[]>(EMPLOYEE_ENDPOINT, { params });
    return response.data;
  },
  
  getById: async (id: number) => {
    const response = await api.get<Employee>(`${EMPLOYEE_ENDPOINT}${id}/`);
    return response.data;
  },

  create: async (data: Partial<Employee>) => {
    const response = await api.post<Employee>(EMPLOYEE_ENDPOINT, data);
    return response.data;
  },

  update: async (id: number, data: Partial<Employee>) => {
    const response = await api.patch<Employee>(`${EMPLOYEE_ENDPOINT}${id}/`, data);
    return response.data;
  },

  archive: async (id: number) => {
    const response = await api.post(`${EMPLOYEE_ENDPOINT}${id}/archive/`);
    return response.data;
  },

  // Family Members
  getFamilyMembers: async (employeeId: number) => {
    const response = await api.get<FamilyMember[]>(`${EMPLOYEE_ENDPOINT}${employeeId}/family-members/`);
    return response.data;
  },

  addFamilyMember: async (employeeId: number, data: FamilyMember) => {
    const response = await api.post<FamilyMember>(`${EMPLOYEE_ENDPOINT}${employeeId}/family-members/`, data);
    return response.data;
  },

  // Documents
  getDocuments: async (employeeId: number) => {
    const response = await api.get<EmployeeDocument[]>(`${EMPLOYEE_ENDPOINT}${employeeId}/documents/`);
    return response.data;
  },

  addDocument: async (employeeId: number, formData: FormData) => {
    const response = await api.post<EmployeeDocument>(`${EMPLOYEE_ENDPOINT}${employeeId}/documents/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Education and Experience
  getEducationAndExperience: async (employeeId: number) => {
    const response = await api.get<EducationAndExperience[]>(`${EMPLOYEE_ENDPOINT}${employeeId}/education/`);
    return response.data;
  },

  addEducationAndExperience: async (employeeId: number, data: EducationAndExperience) => {
    const response = await api.post<EducationAndExperience>(`${EMPLOYEE_ENDPOINT}${employeeId}/education/`, data);
    return response.data;
  },
  
  // History
  getHistory: async (employeeId: number) => {
    const response = await api.get(`${EMPLOYEE_ENDPOINT}${employeeId}/history/`);
    return response.data;
  }
};
