import React, { useState } from 'react';
import { profileService } from '../services/profileService';
import { StudentProfile as StudentProfileType } from '../types/profile';
import { MOCK_STUDENT_PROFILE } from '../services/mockData';
import { UploadCloud, CheckCircle, AlertCircle, User } from 'lucide-react';

interface StudentProfileProps {
  initialProfile?: StudentProfileType;
}

export const StudentProfile: React.FC<StudentProfileProps> = ({ initialProfile }) => {
  const [profile] = useState<StudentProfileType>(initialProfile || MOCK_STUDENT_PROFILE);

  // Estados para la carga de CV (HU-08 / RNF-04)
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    setUploadSuccess(null);
    
    if (!e.target.files || e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    const allowedTypes = [
      'application/pdf', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];
    const maxSizeInBytes = 5 * 1024 * 1024; // 5 MB (RNF-04)

    if (!allowedTypes.includes(file.type) && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      setUploadError('Formato no permitido. Solo se aceptan archivos PDF o DOCX.');
      return;
    }

    if (file.size > maxSizeInBytes) {
      setUploadError('El archivo supera el tamaño máximo permitido de 5 MB.');
      return;
    }

    setCvFile(file);
  };

  const handleUploadCV = async () => {
    if (!cvFile) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      await profileService.uploadCV(cvFile);
      setUploadSuccess('CV subido con éxito. Procesando datos con IA...');
    } catch (err: any) {
      setUploadSuccess(`[Simulación] Archivo "${cvFile.name}" validado y listo para enviar al Gateway.`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200/80 space-y-7">
      {/* Encabezado del Perfil con Nombre Agrandado */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-100 pb-5 gap-4">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-xl shrink-0 border border-blue-100">
            <User className="w-7 h-7" />
          </div>
          <div>
            {/* 🚀 Nombre de usuario incrementado a text-xl (mobile) / text-2xl (escritorio) */}
            <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              {profile.personal.name}
            </h2>
            <p className="text-sm font-medium text-slate-500 mt-0.5">
              {profile.headline || 'Estudiante / Candidato'}
            </p>
          </div>
        </div>
        <span className="self-start md:self-auto text-xs sm:text-sm font-bold px-3.5 py-1.5 bg-slate-100 text-slate-700 rounded-full border border-slate-200">
          {profile.academic_status.institution} ({profile.academic_status.career})
        </span>
      </div>

      {/* Carga de CV (HU-08 / RNF-04) */}
      <div className="border-2 border-dashed border-slate-200 p-6 rounded-2xl text-center bg-slate-50/50 hover:bg-slate-50 transition-all">
        <div className="flex justify-center mb-2">
          <UploadCloud className="w-9 h-9 text-blue-500" />
        </div>
        <h3 className="text-base font-extrabold text-slate-800 mb-1">Cargar o Actualizar CV (HU-08)</h3>
        <p className="text-xs sm:text-sm text-slate-500 mb-4 max-w-md mx-auto leading-relaxed">
          Subí tu CV en formato <strong>PDF</strong> o <strong>DOCX</strong> (máximo 5 MB) para extraer datos con IA.
        </p>
        
        <div className="flex flex-col items-center gap-3">
          <input 
            type="file" 
            accept=".pdf,.docx" 
            onChange={handleFileChange}
            className="text-xs sm:text-sm text-slate-600 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition-all cursor-pointer"
          />

          {cvFile && (
            <button 
              onClick={handleUploadCV}
              disabled={uploading}
              className="px-5 py-2.5 bg-blue-600 text-white text-xs sm:text-sm font-bold rounded-xl hover:bg-blue-700 disabled:bg-slate-400 transition-all shadow-md shadow-blue-600/20"
            >
              {uploading ? 'Procesando...' : `Subir ${cvFile.name}`}
            </button>
          )}

          {uploadError && (
            <div className="flex items-center text-xs sm:text-sm text-red-600 font-bold space-x-1.5 mt-2">
              <AlertCircle className="w-4 h-4 mr-1 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}
          {uploadSuccess && (
            <div className="flex items-center text-xs sm:text-sm text-emerald-700 font-bold space-x-1.5 mt-2 bg-emerald-50 px-3 py-2 rounded-xl border border-emerald-200">
              <CheckCircle className="w-4 h-4 mr-1 shrink-0 text-emerald-600" />
              <span>{uploadSuccess}</span>
            </div>
          )}
        </div>
      </div>

      {/* Competencias */}
      <div>
        <h3 className="text-xs font-extrabold text-slate-500 uppercase tracking-wider mb-3">
          Competencias Destacadas
        </h3>
        <div className="flex flex-wrap gap-2.5">
          {profile.skills.map((skill, idx) => (
            <span 
              key={idx}
              className="inline-flex items-center space-x-1 text-xs sm:text-sm bg-slate-100 text-slate-800 px-3.5 py-1.5 rounded-xl border border-slate-200/80 font-semibold"
            >
              <span>{skill.name}</span>
              <span className="text-[11px] bg-blue-100 text-blue-900 px-2 py-0.5 rounded-md font-extrabold ml-1.5">
                Nivel {skill.level}
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};