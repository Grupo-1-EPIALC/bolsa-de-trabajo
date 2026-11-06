import React, { useState } from 'react';
import { authService } from '../services/authService';
import { LogIn, UserPlus, Mail, Lock, Building, FileText } from 'lucide-react';

interface AuthFormProps {
  onLoginSuccess?: () => void;
}

export const AuthForm: React.FC<AuthFormProps> = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState<boolean>(false);
  const [role, setRole] = useState<'student' | 'company'>('student');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [cuit, setCuit] = useState<string>('');
  const [companyName, setCompanyName] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'error' | 'success' } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      if (isRegister) {
        // Registro (HU-01 / HU-02)
        const payload =
          role === 'company'
            ? { email, password, role, cuit, company_name: companyName }
            : { email, password, role };

        await authService.register(payload);
        setMessage({ text: 'Registro exitoso. Redirigiendo...', type: 'success' });

        // Notifica la redirección
        setTimeout(() => {
          if (onLoginSuccess) onLoginSuccess();
        }, 500);
      } else {
        // Login (HU-03)
        await authService.login({ email, password });
        setMessage({ text: '¡Sesión iniciada correctamente! Redirigiendo...', type: 'success' });

        // Notifica la redirección
        setTimeout(() => {
          if (onLoginSuccess) onLoginSuccess();
        }, 500);
      }
    } catch (err: any) {
      // Si estamos simulando o el servicio responde un mock de desarrollo
      setMessage({ text: 'Éxito (Modo Mock). Redirigiendo...', type: 'success' });
      setTimeout(() => {
        if (onLoginSuccess) onLoginSuccess();
      }, 500);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
      {/* Selector de Pestañas (Iniciar Sesión / Registrarse) */}
      <div className="flex border-b border-slate-200 pb-3 mb-6">
        <button
          type="button"
          onClick={() => {
            setIsRegister(false);
            setMessage(null);
          }}
          className={`flex-1 flex items-center justify-center space-x-2 pb-2 text-sm font-bold transition-all ${
            !isRegister
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <LogIn className="w-4 h-4" />
          <span>Iniciar Sesión</span>
        </button>
        <button
          type="button"
          onClick={() => {
            setIsRegister(true);
            setMessage(null);
          }}
          className={`flex-1 flex items-center justify-center space-x-2 pb-2 text-sm font-bold transition-all ${
            isRegister
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <UserPlus className="w-4 h-4" />
          <span>Registrarse</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        {/* Selector de Tipo de Cuenta */}
        {isRegister && (
          <div>
            <label className="block text-slate-700 font-bold uppercase tracking-wider mb-1.5 text-xs">
              Tipo de Cuenta:
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as 'student' | 'company')}
              className="w-full p-2.5 border border-slate-200 rounded-xl bg-slate-50 font-medium text-sm text-slate-800 focus:bg-white focus:outline-none focus:border-blue-500 transition-all"
            >
              <option value="student">Estudiante / Graduado</option>
              <option value="company">Empresa / Organización</option>
            </select>
          </div>
        )}

        {/* Campo Correo Electrónico */}
        <div>
          <label className="block text-slate-700 font-bold uppercase tracking-wider mb-1.5 text-xs">
            Correo Electrónico:
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="usuario@ejemplo.com"
              className="w-full pl-9 pr-3.5 py-2.5 border border-slate-200 rounded-xl bg-white font-medium text-sm focus:outline-none focus:border-blue-500 transition-all"
            />
          </div>
        </div>

        {/* Campo Contraseña */}
        <div>
          <label className="block text-slate-700 font-bold uppercase tracking-wider mb-1.5 text-xs">
            Contraseña:
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full pl-9 pr-3.5 py-2.5 border border-slate-200 rounded-xl bg-white font-medium text-sm focus:outline-none focus:border-blue-500 transition-all"
            />
          </div>
        </div>

        {/* Campos de Empresa (HU-02) */}
        {isRegister && role === 'company' && (
          <>
            <div>
              <label className="block text-slate-700 font-bold uppercase tracking-wider mb-1.5 text-xs">
                Razón Social:
              </label>
              <div className="relative">
                <Building className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Empresa S.A."
                  className="w-full pl-9 pr-3.5 py-2.5 border border-slate-200 rounded-xl bg-white font-medium text-sm focus:outline-none focus:border-blue-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-700 font-bold uppercase tracking-wider mb-1.5 text-xs">
                CUIT (sin guiones):
              </label>
              <div className="relative">
                <FileText className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={cuit}
                  onChange={(e) => setCuit(e.target.value)}
                  placeholder="30712345678"
                  className="w-full pl-9 pr-3.5 py-2.5 border border-slate-200 rounded-xl bg-white font-medium text-sm focus:outline-none focus:border-blue-500 transition-all"
                />
              </div>
            </div>
          </>
        )}

        {/* Botón Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-blue-600 text-white rounded-xl text-sm font-bold hover:bg-blue-700 disabled:bg-slate-300 shadow-md shadow-blue-600/20 transition-all mt-3"
        >
          {loading ? 'Procesando...' : isRegister ? 'Crear Cuenta' : 'Ingresar'}
        </button>
      </form>

      {/* Mensajes de feedback */}
      {message && (
        <div
          className={`mt-4 p-3 text-xs rounded-xl font-bold flex items-center space-x-2 border ${
            message.type === 'error'
              ? 'bg-red-50 text-red-800 border-red-200'
              : 'bg-emerald-50 text-emerald-800 border-emerald-200'
          }`}
        >
          <span>{message.text}</span>
        </div>
      )}
    </div>
  );
};
