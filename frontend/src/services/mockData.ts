import { StudentProfile } from '../types/profile';
import { JobOpportunity } from '../types/jobs';

export const MOCK_STUDENT_PROFILE: StudentProfile = {
  id: 'prof-estudiante-01',
  user_id: 'user-123',
  personal: {
    name: 'Lucía Pérez',
    email: 'lucia.perez@example.com',
    phone: '+54 11 4433-2211',
    location: { country: 'AR', province: 'Buenos Aires', city: 'San Isidro' },
  },
  headline: 'Estudiante de Ing. en Sistemas – Desarrollo Web',
  academic_status: {
    institution: 'UTN FRBA',
    career: 'Ing. en Sistemas',
    current_year: 4,
    progress_percent: 70,
  },
  skills: [
    { name: 'React', normalized: 'react', level: 3, source: 'cv_ai', confirmed: true },
    { name: 'TypeScript', normalized: 'typescript', level: 2, source: 'manual', confirmed: true },
    { name: 'Git', normalized: 'git', level: 3, source: 'manual', confirmed: true },
  ],
  experience: [],
  education: [],
  languages: [{ name: 'Inglés', normalized: 'ingles', level: 'B2' }],
  visibility: 'public_to_companies',
  job_search_status: 'active',
};

export const MOCK_JOB_OPPORTUNITY: JobOpportunity = {
  id: 'job-01',
  company_id: 'comp-99',
  title: 'Desarrollador/a Frontend Trainee',
  description: 'Buscamos estudiante avanzado para sumarse al equipo de desarrollo SPA con React.',
  status: 'active',
  seniority: 'trainee',
  vacancies: 2,
  location: { country: 'AR', province: 'CABA', city: 'Buenos Aires' },
  work_conditions: {
    work_schedule: ['part_time'],
    work_modality: ['hybrid'],
    employment_type: ['internship'],
  },
  requirements: {
    skills: [
      { name: 'React', normalized: 'react', level: 2, kind: 'required', source: 'manual' },
      { name: 'TypeScript', normalized: 'typescript', level: 2, kind: 'desired', source: 'manual' },
      { name: 'Docker', normalized: 'docker', level: 3, kind: 'required', source: 'manual' },
    ],
  },
};