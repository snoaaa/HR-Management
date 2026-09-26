import { useState, useCallback } from 'react';
import { employeeService } from '../api/employeeService';
import type { Employee } from '../types/employee';

export const useEmployees = () => {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEmployees = useCallback(async (params?: Record<string, any>) => {
    setLoading(true);
    setError(null);
    try {
      const data = await employeeService.getAll(params);
      setEmployees(data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to fetch employees');
    } finally {
      setLoading(false);
    }
  }, []);

  const getEmployee = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await employeeService.getById(id);
      return data;
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to fetch employee');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const createEmployee = async (data: Partial<Employee>) => {
    setLoading(true);
    setError(null);
    try {
      const newEmployee = await employeeService.create(data);
      setEmployees(prev => [newEmployee, ...prev]);
      return newEmployee;
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to create employee');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updateEmployee = async (id: number, data: Partial<Employee>) => {
    setLoading(true);
    setError(null);
    try {
      const updatedEmployee = await employeeService.update(id, data);
      setEmployees(prev => prev.map(emp => emp.id === id ? updatedEmployee : emp));
      return updatedEmployee;
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to update employee');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const archiveEmployee = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      await employeeService.archive(id);
      setEmployees(prev => prev.map(emp => emp.id === id ? { ...emp, status: 'ARCHIVED' } : emp));
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to archive employee');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    employees,
    loading,
    error,
    fetchEmployees,
    getEmployee,
    createEmployee,
    updateEmployee,
    archiveEmployee
  };
};
