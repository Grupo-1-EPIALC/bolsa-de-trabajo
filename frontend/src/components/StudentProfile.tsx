import React, { useState } from 'react';
import { StudentProfile as StudentProfileType } from '../types/profile';

export const StudentProfile: React.FC = () => {
  // Estado mock basado en el contrato borrador v0.1.0-draft (§5 y §8)
  const [profile] = useState<StudentProfileType>({
    id: 'prof-estudiante-01',
    user_id: 'user-123',
    personal: {
      name: 'Lucía Pérez',
      email: 'lucia.perez@example.com',
      phone: '+54 11 4433-2211',
      location: { country: 'AR', province: 'Buenos Aires', city: 'San Isidro' },
    },
    headline: 'Estudiante de Ing. en Sistemas – Desarrollo Web',
    summary: 'Apasionada por el desarrollo frontend con React y la integración de herramientas agénticas de IA.',
    academic_status: {
      institution: 'UTN FRBA',
      career: 'Ing. en Sistemas',
      current_year: 4,
      progress_percent: 70,
      student_shift: ['evening'],
    },
    work_conditions: {
      work_schedule: ['part_time'],
      work_modality: ['hybrid', 'remote'],
      hybrid_onsite_days: 2,
      employment_type: ['employee', 'internship'],
      salary: {
        min: 600000,
        max: 750000,
        currency: 'ARS',
        period: 'month',
        visibility: 'on_match',
      },
    },
    skills: [
      { name: 'React', normalized: 'react', level: 3, source: 'cv_ai', confirmed: true },
      { name: 'TypeScript', normalized: 'typescript', level: 2, source: 'manual', confirmed: true },
      { name: 'Git', normalized: 'git', level: 3, source: 'manual', confirmed: true },
    ],
    experience: [],
    education: [
      {
        institution: 'UTN FRBA',
        degree: 'Ingeniería en Sistemas de Información',
        level: 'university',
        status: 'in_progress',
        progress_percent: 70,
      },
    ],
    languages: [{ name: 'Inglés', normalized: 'ingles', level: 'B2' }],
    visibility: 'public_to_companies',
    job_search_status: 'active',
  });

  return (
    <div className="bg-white p-6 rounded-lg shadow-md space-y-6">
      {/* Encabezado del Perfil */}
      <div className="border-b pb-4 flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{profile.personal.name}</h2>
          <p className="text-sm font-medium text-blue-600">{profile.headline}</p>
          <p className="text-xs text-gray-500 mt-1">
            📍 {profile.personal.location.city}, {profile.personal.location.province} | 🎓 {profile.academic_status.career} ({profile.academic_status.institution})
          </p>
        </div>
        <span className="bg-green-100 text-green-800 text-xs px-3 py-1 rounded-full font-bold uppercase">
          Búsqueda: {profile.job_search_status}
        </span>
      </div>

      {/* Carga de CV (HU-08 / HU-09) */}
      <div className="border-2 border-dashed border-gray-300 p-6 rounded-lg text-center bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Cargar o Actualizar CV (HU-08)</h3>
        <p className="text-xs text-gray-500 mb-3">
          Subí tu CV en formato <strong>PDF</strong> o <strong>DOCX</strong> (máximo 5 MB) para extraer datos con IA.
        </p>
        <button className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded hover:bg-blue-700">
          Seleccionar Archivo PDF/DOCX
        </button>
      </div>

      {/* Grid de Secciones */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Competencias Confimadas */}
        <div className="bg-gray-50 p-4 rounded border">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Competencias (Skills)</h3>
          <div className="flex flex-wrap gap-2">
            {profile.skills.map((skill, idx) => (
              <span key={idx} className="bg-blue-100 text-blue-900 text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1">
                {skill.name} (Nivel {skill.level})
                {skill.source === 'cv_ai' && <span title="Extraído por IA">🤖</span>}
              </span>
            ))}
          </div>
        </div>

        {/* Preferencias de Trabajo */}
        <div className="bg-gray-50 p-4 rounded border">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Preferencias Laborales</h3>
          <ul className="text-xs space-y-1.5 text-gray-600">
            <li><strong>Modalidad:</strong> {profile.work_conditions?.work_modality?.join(', ')}</li>
            <li><strong>Jornada:</strong> {profile.work_conditions?.work_schedule?.join(', ')}</li>
            <li>
              <strong>Pretensión Salarial:</strong> ${profile.work_conditions?.salary?.min?.toLocaleString()} - ${profile.work_conditions?.salary?.max?.toLocaleString()} {profile.work_conditions?.salary?.currency}
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};