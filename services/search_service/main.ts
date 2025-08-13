import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { typesenseClient } from './modules/search/typesense.client';
import * as dotenv from 'dotenv';

dotenv.config(); // load .env config early

async function createSchemaIfNotExists() {
  try {
    // Try to retrieve the collection
    await typesenseClient.collections('products').retrieve();
    console.log('✅ Collection "products" already exists — skipping creation.');
  } catch (err: any) {
    if (err?.httpStatus === 404) {
      console.log('⚠️ Collection "products" not found — creating...');
      try {
        await typesenseClient.collections().create({
          name: 'products',
          fields: [
            { name: 'id', type: 'string' },
            { name: 'productname', type: 'string' },
            { name: 'category', type: 'string', facet: true },
            { name: 'manufacturer', type: 'string', facet: true },
            { name: 'subcategory', type: 'string', facet: true },
            { name: 'semicon_part_number', type: 'string', facet: true },
            { name: 'manufacturer_part_number', type: 'string', facet: true },
          ],
        });
        console.log('✅ Created new Typesense collection "products".');
      } catch (createErr) {
        console.error('❌ Failed to create schema:', createErr);
        console.warn('⚠️ Continuing without Typesense collection — indexing will fail until fixed.');
      }
    } else {
      console.error('❌ Failed to check collection existence:', err);
      console.warn('⚠️ Continuing without Typesense connection — search may not work.');
    }
  }
}

async function bootstrap() {
  await createSchemaIfNotExists();

  const app = await NestFactory.create(AppModule);
  const PORT = process.env.PORT || 8004;
  await app.listen(PORT);
  console.log(`🚀 Search Service running at http://localhost:${PORT}`);
}

bootstrap();
