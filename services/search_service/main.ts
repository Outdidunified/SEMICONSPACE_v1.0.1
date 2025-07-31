import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { typesenseClient } from './modules/search/typesense.client';

async function createSchemaIfNotExists() {
  try {
    await typesenseClient.collections().create({
      name: 'products',
      fields: [
        { name: 'id', type: 'string' },
        { name: 'product_id', type: 'int32' },
        { name: 'external_product_id', type: 'string' },
        { name: 'supplier', type: 'string', facet: true },
        { name: 'name', type: 'string' },
        { name: 'description', type: 'string' },
        { name: 'manufacturer_id', type: 'int32' },
        { name: 'manufacturer_part_number', type: 'string' },
        { name: 'quantity', type: 'int32' },
        { name: 'category', type: 'string', facet: true },
        { name: 'package_type', type: 'string' },
        { name: 'datasheet_url', type: 'string' },
        { name: 'image_url', type: 'string' },
        { name: 'last_fetched_at', type: 'string' }, // ISO datetime as string
        { name: 'created_at', type: 'string' },
        { name: 'category_id', type: 'int32' },
        { name: 'created_by', type: 'string' },
        { name: 'created_date', type: 'string' },
        { name: 'modified_by', type: 'string' },
        { name: 'modified_date', type: 'string' },
        { name: 'status', type: 'bool' }
      ],
    });
    console.log('Typesense schema created!');
  } catch (err) {
    if (err.message.includes('already exists')) {
      console.log(' Schema already exists — skipping creation.');
    } else {
      console.error(' Failed to create schema:', err);
    }
  }
}

async function bootstrap() {
  await createSchemaIfNotExists();

  const app = await NestFactory.create(AppModule);
  await app.listen(8004); // Now runs HTTP server for /search endpoint
  console.log(' Search Service running at http://localhost:8004');
}
bootstrap();
