import React from 'react';

export const AuthForm: React.FC = () => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md max-w-md mx-auto space-y-4">
      <h2 className="text-xl font-semibold text-gray-800 border-b pb-2 text-center">
        Iniciar Sesión (HU-03)
      </h2>
      <form onSubmit={(e) => e.preventDefault()} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-600 mb-1">Correo Electrónico</label>
          <input
            type="email"
            placeholder="estudiante@ejemplo.com"
            className="w-full p-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-600 mb-1">Contraseña</label>
          <input
            type="password"
            placeholder="••••••••"
            className="w-full p-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="button"
          className="w-full py-2 bg-blue-600 text-white font-medium rounded text-sm hover:bg-blue-700"
        >
          Ingresar
        </button>
      </form>
    </div>
  );
};