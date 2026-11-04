import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch()
export class HttpExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(HttpExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const context = host.switchToHttp();
    const response = context.getResponse<Response>();
    const request = context.getRequest<Request>();
    const status =
      exception instanceof HttpException ? exception.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR;

    if (!(exception instanceof HttpException)) {
      this.logger.error(
        `Unhandled error for ${request.method} ${request.url}`,
        exception instanceof Error ? exception.stack : String(exception),
      );
    }

    const responseBody = exception instanceof HttpException ? exception.getResponse() : null;
    const message =
      typeof responseBody === 'object' && responseBody !== null && 'message' in responseBody
        ? (responseBody as { message: string | string[] }).message
        : status === HttpStatus.INTERNAL_SERVER_ERROR
          ? 'Error interno del servidor'
          : exception instanceof Error
            ? exception.message
            : 'Error en la solicitud';
    const code =
      typeof responseBody === 'object' &&
      responseBody !== null &&
      'error' in responseBody &&
      typeof (responseBody as { error: unknown }).error === 'string'
        ? (responseBody as { error: string }).error.toUpperCase().replaceAll(' ', '_')
        : status === HttpStatus.INTERNAL_SERVER_ERROR
          ? 'INTERNAL_SERVER_ERROR'
          : `HTTP_${status}`;

    response.status(status).json({
      error: {
        code,
        message,
        details: Array.isArray(message) ? { validation_errors: message } : {},
      },
    });
  }
}
