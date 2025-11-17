/**
 * Meters API Route
 *
 * Provides CRUD operations for meter management
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import type { Prisma } from '@prisma/client';

export const dynamic = 'force-dynamic';

/**
 * GET /api/config/meters
 * Get all meters, optionally filtered by type or category
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const meterType = searchParams.get('type');
    const category = searchParams.get('category');
    const activeOnly = searchParams.get('active') !== 'false';

    const where: Prisma.MeterWhereInput = {};

    if (meterType) {
      where.meterType = meterType;
    }

    if (category) {
      where.category = category;
    }

    if (activeOnly) {
      where.active = true;
    }

    const meters = await prisma.meter.findMany({
      where,
      orderBy: { id: 'asc' },
      include: {
        householdMeters: {
          include: {
            household: {
              select: {
                id: true,
                name: true,
              },
            },
          },
        },
      },
    });

    return NextResponse.json({ meters });
  } catch (error) {
    console.error('Failed to fetch meters:', error);
    return NextResponse.json(
      { error: 'Failed to fetch meters' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/config/meters
 * Create a new meter
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();

    const {
      id,
      name,
      meterType,
      category,
      unit,
      installationDate,
      deinstallationDate,
      sourceMeters,
      calculationConfig,
      active = true,
    } = body;

    // Validate required fields
    if (!id || !name || !meterType || !category || !unit) {
      return NextResponse.json(
        { error: 'Missing required fields: id, name, meterType, category, unit' },
        { status: 400 }
      );
    }

    // Validate meter type
    const validMeterTypes = ['electricity', 'gas', 'water', 'heat', 'solar'];
    if (!validMeterTypes.includes(meterType)) {
      return NextResponse.json(
        { error: `Invalid meterType. Must be one of: ${validMeterTypes.join(', ')}` },
        { status: 400 }
      );
    }

    // Validate category
    const validCategories = ['physical', 'master', 'virtual'];
    if (!validCategories.includes(category)) {
      return NextResponse.json(
        { error: `Invalid category. Must be one of: ${validCategories.join(', ')}` },
        { status: 400 }
      );
    }

    const meter = await prisma.meter.create({
      data: {
        id,
        name,
        meterType,
        category,
        unit,
        installationDate: installationDate ? new Date(installationDate) : null,
        deinstallationDate: deinstallationDate ? new Date(deinstallationDate) : null,
        sourceMeters: sourceMeters || null,
        calculationConfig: calculationConfig || null,
        active,
      },
    });

    return NextResponse.json({ meter }, { status: 201 });
  } catch (error: any) {
    console.error('Failed to create meter:', error);

    if (error.code === 'P2002') {
      return NextResponse.json(
        { error: 'Meter ID already exists' },
        { status: 409 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to create meter' },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/config/meters?id=meter_id
 * Update an existing meter
 */
export async function PATCH(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const meterId = searchParams.get('id');

    if (!meterId) {
      return NextResponse.json(
        { error: 'Meter ID is required' },
        { status: 400 }
      );
    }

    const body = await request.json();

    const updateData: Prisma.MeterUpdateInput = {};

    if (body.name !== undefined) updateData.name = body.name;
    if (body.meterType !== undefined) updateData.meterType = body.meterType;
    if (body.category !== undefined) updateData.category = body.category;
    if (body.unit !== undefined) updateData.unit = body.unit;
    if (body.installationDate !== undefined) {
      updateData.installationDate = body.installationDate ? new Date(body.installationDate) : null;
    }
    if (body.deinstallationDate !== undefined) {
      updateData.deinstallationDate = body.deinstallationDate ? new Date(body.deinstallationDate) : null;
    }
    if (body.sourceMeters !== undefined) updateData.sourceMeters = body.sourceMeters;
    if (body.calculationConfig !== undefined) updateData.calculationConfig = body.calculationConfig;
    if (body.active !== undefined) updateData.active = body.active;

    const meter = await prisma.meter.update({
      where: { id: meterId },
      data: updateData,
    });

    return NextResponse.json({ meter });
  } catch (error: any) {
    console.error('Failed to update meter:', error);

    if (error.code === 'P2025') {
      return NextResponse.json(
        { error: 'Meter not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to update meter' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/config/meters?id=meter_id
 * Delete a meter
 */
export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const meterId = searchParams.get('id');

    if (!meterId) {
      return NextResponse.json(
        { error: 'Meter ID is required' },
        { status: 400 }
      );
    }

    await prisma.meter.delete({
      where: { id: meterId },
    });

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error('Failed to delete meter:', error);

    if (error.code === 'P2025') {
      return NextResponse.json(
        { error: 'Meter not found' },
        { status: 404 }
      );
    }

    if (error.code === 'P2003') {
      return NextResponse.json(
        { error: 'Cannot delete meter: it is assigned to households' },
        { status: 409 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to delete meter' },
      { status: 500 }
    );
  }
}
