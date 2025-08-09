import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { typesenseClient } from './modules/search/typesense.client';

async function createSchemaIfNotExists() {
  try {
    // First, delete old collection if it exists
    try {
      await typesenseClient.collections('products').delete();
      console.log('🗑 Old "products" collection deleted.');
    } catch {
      console.log('ℹ No existing "products" collection to delete.');
    }

    // Create new collection without status field
    await typesenseClient.collections().create({
      name: 'products',
      fields: [
        { name: 'id', type: 'string' },
        { name: 'productname', type: 'string' },
        { name: 'category', type: 'string', facet: true },
        { name: 'manufacturer', type: 'string', facet: true },
        { name: 'subcategory', type: 'string', facet: true }
      ]
    });

    console.log('✅ New Typesense schema created (no status field).');
  } catch (err) {
    console.error('❌ Failed to create schema:', err);
  }
}

async function bootstrap() {
  await createSchemaIfNotExists();

  const app = await NestFactory.create(AppModule);
  await app.listen(8004);
  console.log('🚀 Search Service running at http://localhost:8004');
}

bootstrap();
