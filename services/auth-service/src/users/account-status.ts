/** Estado operativo de una cuenta. El borrado lógico se indica aparte con `deleted_at`. */
export enum AccountStatus {
  ACTIVE = 'active',
  SUSPENDED = 'suspended',
}
