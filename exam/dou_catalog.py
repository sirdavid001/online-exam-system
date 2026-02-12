DOU_FACULTY_DEPARTMENTS = {
    "Faculty of Agriculture": [
        "Animal Science",
        "Crop Science",
        "Soil Science",
    ],
    "Faculty of Allied Health Sciences": [
        "Nursing Science",
    ],
    "Faculty of Arts": [
        "English and Literary Studies",
        "Fine and Applied Arts",
        "History and International Studies",
        "Language and Linguistics",
    ],
    "Faculty of Basic Medical Sciences": [
        "Human Anatomy",
        "Human Physiology",
        "Medical Biochemistry",
    ],
    "Faculty of Behavioral and Social Sciences": [
        "Economics",
        "Mass Communication",
        "Political Science",
        "Psychology",
        "Sociology",
    ],
    "Faculty of Computing": [
        "Computer Science",
        "Cyber Security",
        "Data Science",
        "Information Technology",
        "Software Engineering",
    ],
    "Faculty of Environmental Sciences": [
        "Architecture",
        "Building",
        "Environmental Management",
        "Estate Management",
        "Quantity Surveying",
    ],
    "Faculty of Law": [
        "Law",
    ],
    "Faculty of Management Sciences": [
        "Accounting",
        "Banking and Finance",
        "Business Administration",
        "Marketing",
        "Public Administration",
    ],
    "Faculty of Science": [
        "Animal and Environmental Biology",
        "Biochemistry",
        "Biology",
        "Chemistry",
        "Environmental Management and Toxicology",
        "Geology",
        "Marine Science",
        "Mathematics",
        "Microbiology",
        "Physics",
        "Plant Science and Biotechnology",
        "Science Laboratory Technology",
    ],
}


def faculty_choices(include_blank=True):
    choices = [(name, name) for name in DOU_FACULTY_DEPARTMENTS.keys()]
    if include_blank:
        return [("", "Select Faculty")] + choices
    return choices


def department_choices_for(faculty_name, include_blank=True):
    departments = DOU_FACULTY_DEPARTMENTS.get(faculty_name, [])
    choices = [(name, name) for name in departments]
    if include_blank:
        blank_label = "Select Department" if departments else "Select Faculty First"
        return [("", blank_label)] + choices
    return choices
