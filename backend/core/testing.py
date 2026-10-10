"""Helpers shared by the test suites of every module."""

import datetime

from rest_framework.test import APIClient

from employees.models import Employee
from organisation.models import Classification, Department, Position, Site
from users.models import User


def make_user(username, role=User.Roles.EMPLOYEE, **extra):
    user = User.objects.create_user(
        username=username, password="Passw0rd!", role=role, **extra
    )
    user.requires_password_change = False
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_structure():
    site = Site.objects.create(name="HQ", code="HQ")
    department = Department.objects.create(name="Engineering", code="ENG", site=site)
    other_department = Department.objects.create(name="Sales", code="SAL", site=site)
    classification = Classification.objects.create(
        category="Employee", grade="B", echelon="1"
    )
    position = Position.objects.create(
        title="Developer", code="DEV", classification=classification
    )
    return {
        "site": site,
        "department": department,
        "other_department": other_department,
        "classification": classification,
        "position": position,
    }


def make_employee(structure, user=None, department=None, **extra):
    data = {
        "surname": "Doe",
        "given_names": "John",
        "date_of_birth": datetime.date(1990, 1, 1),
        "place_of_birth": "Douala",
        "sex": "M",
        "nationality": "Cameroonian",
        "marital_status": "SINGLE",
        "identity_document_type": "ID Card",
        "identity_document_number": "123",
        "address": "Akwa",
        "phone_number": "600000000",
        "emergency_contact_name": "Jane",
        "emergency_contact_number": "611111111",
        "contract_type": "PERMANENT",
        "date_of_hire": datetime.date(2020, 1, 1),
        "department": department or structure["department"],
        "position": structure["position"],
        "classification": structure["classification"],
        "workplace": structure["site"],
        "status": "ACTIVE",
        "user": user,
    }
    data.update(extra)
    return Employee.objects.create(**data)
