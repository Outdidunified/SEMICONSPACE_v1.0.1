import { Injectable, Logger } from '@nestjs/common';
import * as nodemailer from 'nodemailer';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class MailService {
  private readonly logger = new Logger(MailService.name);
  private transporter: nodemailer.Transporter;

  constructor(private readonly configService: ConfigService) {
    this.transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: 'info@outdidunified.com',
    pass: 'yylhzjwopsvrslqb',
  },
});

  }

  async sendMail(to: string, subject: string, message: string): Promise<void> {
    try {
      const info = await this.transporter.sendMail({
        from: `"Semicon Space" <${this.configService.get<string>('GMAIL_USER')}>`,
        to,
        subject,
        html: message,
      });

      this.logger.log(`📧 Email sent to ${to}: ${info.messageId}`);
    } catch (error) {
      this.logger.error(`❌ Failed to send email to ${to}`, error);
    }
  }
}
