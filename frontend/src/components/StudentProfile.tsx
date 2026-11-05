import React, { useState, useEffect } from 'react';
import { profileService } from '../services/profileService';
import { StudentProfile as StudentProfileType } from '../types/profile';
import { MOCK_STUDENT_PROFILE } from '../services/mockData';
import { UploadCloud, User } from 'lucide-react';

interface StudentProfileProps {
  initialProfile?: StudentProfileType;
}

export const StudentProfile: React.FC<StudentProfileProps> = ({ initialProfile }) => {
  const [profile, setProfile] = useState<StudentProfileType>(initialProfile || MOCK_STUDENT_PROFILE);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Estados para subida de CV (HU-08 / RNF-04)
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    profileService.getProfile()
      .then((data) => {
        if (data && Object.keys(data).length > 0) {
          setProfile(data);
        }
        setLoading(false);
      })
      .catch((err: any) => {
        console.error("Error al consultar la API de perfiles:", err);
        setError(err.message || "Error al conectar con la API Gateway");
        setLoading(false);
      });
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const allowedTypes = [
        'application/pdf', 
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ];
      if (!allowedTypes.includes(file.type) && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
        setUploadStatus('Formato no permitido. Solo se aceptan archivos PDF o DOCX.');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setUploadStatus('El archivo supera el tamaño máximo de 5 MB.');
        return;
      }
      setCvFile(file);
      setUploadStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!cvFile) return;
    setUploading(true);
    setUploadStatus(null);
    try {
      const res = await profileService.uploadCV(cvFile);
      setUploadStatus(res.message || `CV "${cvFile.name}" procesado correctamente.`);
    } catch (err: any) {
      setUploadStatus(`Error al subir CV: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-500 font-bold">Cargando perfil...</div>;

  return (
    <div className="bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200/80 space-y-8">
      {/* Encabezado con Nombre Resaltado */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-100 pb-6 gap-4">
        <div className="flex items-center space-x-4">
          <div className="p-3.5 bg-blue-50 text-blue-600 rounded-2xl shrink-0 border border-blue-100">
            <User className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
              {profile.personal.name}
            </h2>
            <p className="text-sm sm:text-base font-semibold text-slate-500 mt-0.5">
              {profile.headline || 'Estudiante / Candidato'}
            </p>
          </div>
        </div>
        <span className="self-start md:self-auto text-xs sm:text-sm font-bold px-4 py-2 bg-slate-100 text-slate-700 rounded-full border border-slate-200 shadow-xs">
          {profile.academic_status.institution} ({profile.academic_status.career})
        </span>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 text-sm font-bold">
          {error} (Mostrando datos locales de respaldo)
        </div>
      )}

      {/* Carga de CV (HU-08 / RNF-04) */}
      <div className="border-2 border-dashed border-slate-200 p-6 sm:p-8 rounded-2xl text-center bg-slate-50/50 hover:bg-slate-50 transition-all">
        <UploadCloud className="w-10 h-10 text-blue-500 mx-auto mb-3" />
        <h3 className="text-lg font-extrabold text-slate-800 mb-1">Cargar o Actualizar CV (HU-08)</h3>
        <p className="text-xs sm:text-sm text-slate-500 mb-4">Formato PDF o DOCX (máximo 5 MB)</p>
        
        <div className="flex flex-col items-center gap-3">
          <input 
            type="file" 
            accept=".pdf,.docx" 
            onChange={handleFileChange}
            className="text-xs sm:text-sm text-slate-600 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition-all cursor-pointer"
          />
          {cvFile && (
            <button 
              onClick={handleUpload} 
              disabled={uploading}
              className="px-5 py-2.5 bg-blue-600 text-white font-bold text-xs sm:text-sm rounded-xl hover:bg-blue-700 disabled:bg-slate-400 transition-all shadow-md shadow-blue-600/20"
            >
              {uploading ? 'Procesando...' : `Subir ${cvFile.name}`}
            </button>
          )}
          {uploadStatus && (
            <div className="flex items-center text-xs sm:text-sm font-bold space-x-1.5 mt-2 bg-slate-100 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700">
              <span>{uploadStatus}</span>
            </div>
          )}
        </div>
      </div>

      {/* Competencias */}
      <div>
        <h3 className="text-xs font-extrabold text-slate-500 uppercase tracking-wider mb-4">
          Competencias Destacadas
        </h3>
        <div className="flex flex-wrap gap-3">
          {profile.skills.map((skill, idx) => (
            <span 
              key={idx}
              className="inline-flex items-center space-x-1.5 text-xs sm:text-sm bg-slate-100 text-slate-800 px-4 py-2 rounded-xl border border-slate-200/80 font-bold shadow-xs"
            >
              <span>{skill.name}</span>
              <span className="text-xs bg-blue-100 text-blue-900 px-2 py-0.5 rounded-md font-extrabold ml-1.5">
                Nivel {skill.level}
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};