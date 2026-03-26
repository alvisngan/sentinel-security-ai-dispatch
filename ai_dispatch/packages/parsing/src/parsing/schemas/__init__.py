from parsing.schemas import client_request, employee_cover, employee_swap

REGISTRY = {
    "client_request": client_request,
    "employee_cover":  employee_cover,
    "employee_swap":   employee_swap,
}
