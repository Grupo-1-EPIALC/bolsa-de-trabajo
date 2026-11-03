import React from 'react';

export const StudentProfile: React.FC = () => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md space-y-4">
      <h2 className="text-xl font-semibold text-gray-800 border-b pb-2">
        Mi Perfil de Estudiante (HU-07 a HU-10)
      </h2>
      
      {/* Sección Carga de CV */}
      <div className="border-2 border-dashed border-gray-300 p-6 rounded-lg text-center bg-gray-50">
        <p className="text-sm text-gray-600 mb-2">
          Cargá tu Currículum Vitae en formato <strong>PDF</strong> o <strong>DOCX</strong> (Máx. 5 MB)
        </p>
        <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">
          Seleccionar archivo
        </button>
      </div>

      {/* Sección Competencias */}
      <div>
        <h3 className="text-md font-semibold text-gray-700 mb-2">Mis Competencias</h3>
        <div className="flex flex-wrap gap-2">
          <span className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full font-medium">
            React (Nivel 2)
          </span>
          <span className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full font-medium">
            TypeScript (Nivel 2)
          </span>
          <span className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full font-medium">
            Git (Nivel 3)
          </span>
        </div>
      </div>
    </div>
  );
};