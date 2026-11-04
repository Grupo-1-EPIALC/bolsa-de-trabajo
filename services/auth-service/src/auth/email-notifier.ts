export const EMAIL_NOTIFIER = Symbol('EMAIL_NOTIFIER');

export interface EmailNotifier {
  sendPasswordReset(to: string, confirmationUrl: string): Promise<void>;
  sendEmailChange(to: string, confirmationUrl: string): Promise<void>;
}
