import { Injectable } from '@nestjs/common';
import * as nodemailer from 'nodemailer';
import { Transporter } from 'nodemailer';
import { EmailNotifier } from './email-notifier';

@Injectable()
export class SmtpEmailNotifier implements EmailNotifier {
  private readonly transporter: Transporter;
  private readonly from = process.env.SMTP_FROM ?? 'no-reply@bolsa.local';

  constructor() {
    const host = process.env.SMTP_HOST;
    if (!host) {
      throw new Error('SMTP_HOST es obligatorio');
    }

    this.transporter = nodemailer.createTransport({
      host,
      port: Number(process.env.SMTP_PORT ?? 1025),
      secure: false,
    });
  }

  async sendPasswordReset(to: string, confirmationUrl: string): Promise<void> {
    await this.transporter.sendMail({
      from: this.from,
      to,
      subject: 'Restablecer contraseña',
      text: `Para restablecer tu contraseña, abrí este enlace: ${confirmationUrl}`,
    });
  }

  async sendEmailChange(to: string, confirmationUrl: string): Promise<void> {
    await this.transporter.sendMail({
      from: this.from,
      to,
      subject: 'Confirmar cambio de email',
      text: `Para confirmar el cambio de email, abrí este enlace: ${confirmationUrl}`,
    });
  }
}
